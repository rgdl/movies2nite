#!/usr/bin/env python
'''
Returns a list of movies on free-to-air TV in Melbourne tonight.
The info is retrieved from 'https://www.yourtv.com.au/guide/'.

Movies are identified by their length (longer than 1 hour) and the 
presence of an IMDB tag in their description. This is not perfect, 
but doesn't appear to miss movies, it just leads to false positives.

Films that have already finished are not shown.

Note: checks for a pickle file in a particular folder. If there's some
unrelated pickle file in that folder, the program will get confused.
'''

# To-do:
# - If first show of tomorrow is same as last show of today, remove one of them before finding end times
# - Checking for an IMBD link isn't reliable. Includes a few false positives.

import urllib2, re, sys, os, pickle
import datetime as dt
from HTMLParser import HTMLParser as HP

now = dt.datetime.now()
one_hour = dt.timedelta(hours=1)
hp = HP()

class Show ():
    def __init__(self, title, starting_time, channel, link):
        self.title = title
        self.channel = channel
        self.starting_time = starting_time
        self.ending_time = '???'
        self.link = link

    def __str__(self):
        time_str = '%-H:%M'
        start_time_str = self.starting_time.strftime(time_str)
        try:
            end_time_str = self.ending_time.strftime(time_str)
        except AttributeError:
            end_time_str = self.ending_time
        output = "%-13s(%s - %s)\t-\t'%s'" % (
            self.channel,
            start_time_str,
            end_time_str,
            self.title
        )
        return hp.unescape(output)

    def get_length(self): # Also adjusts starting/ending times if length is weird
        try:
            duration = self.ending_time - self.starting_time
            if duration < dt.timedelta(0):
                self.starting_time -= dt.timedelta(hours=12)
                return self.get_length()
            elif duration > dt.timedelta(days=1):
                self.ending_time -= dt.timedelta(days=1)
                return self.get_length()
            else:
                return duration
        except:
            return "???"

    def follow_link(self):
        url = 'https://www.yourtv.com.au%s' % self.link
        link_text = urllib2.urlopen(url).read()
        return link_text

    def is_movie(self):
        try:
            link_text = self.follow_link()
            if 'IMDB' in link_text:
                return True
            else:
                return False
        except:
            return True # erring on the side of caution i.e. not removing
            
def text_in_element (text, opening_tag):
    closing_tag = opening_tag[0] + '/' + opening_tag[1:]
    return text.split(opening_tag)[1].split(closing_tag)[0]

def parse_raw_html (page_content, tomorrow=False):
    day_shift = 1 if tomorrow else 0

    # Cut off the stuff after the channels are listed:
    page_content = page_content.split('js-now-pointer')[1]
    
    # Reduce page_content to an array of 'channel' strings: 
    channels = page_content.split('data-channel-logo')

    # Cut off stuff before channels are listed:
    channels = channels[1:]

    # Convert each 'channel' to a list of Show objects, giving a jagged array:
    shows = {}
    for channel in channels:
        # Get name of channel:
        channel_name = channel.split('data-channel-name="')[1].split('"')[0]
        shows[channel_name] = []
        # Iterate through channels, turning shows into Show objects
        for show in channel.split('show-link'):
            try:
                show_time_string = text_in_element(show,'<p>')
                if 'PM' in show_time_string:
                    show_hour = 12 + int(show_time_string.split(':')[0])
                else:
                    show_hour = int(show_time_string.split(':')[0])
                show_minute = int(show_time_string.split(':')[1].split(' ')[0])
                show_time = dt.datetime(now.year, now.month, now.day + day_shift, show_hour, show_minute)
                show_link = re.sub('.*href="(.*) data-event-id.*','\\1',show,1)
                show_link = re.sub('[\s+]','',show_link).split('"')[1]
                shows[channel_name].append(
                    Show(text_in_element(show,'<h4>'), show_time, channel_name, show_link)
                )
            except:
                continue
    return shows

def six_AM_tomorrow():
    output = dt.datetime(now.year, now.month, now.day + 1, 6, 0)    
    return output

def fetch_content():
    print("Fetching content. Please wait...")
    try:
        # Get the pages for today and tomorrow:
        shows_today = urllib2.urlopen('https://www.yourtv.com.au/guide/melbourne/').read()
        shows_tomorrow = urllib2.urlopen('https://www.yourtv.com.au/guide/melbourne/tomorrow').read()
    except urllib2.URLError:
        print "URL issues. Are you connected to the internet?"
        sys.exit(1)
        
    print ("Content fetched. Processing...")

    shows_today = parse_raw_html(shows_today)
    shows_tomorrow = parse_raw_html(shows_tomorrow, tomorrow=True)

    # Match keys (channels) to merge the two collections of shows
    shows = {}
    for channel in shows_today:
        try:
            if shows_today[channel][-1].title == shows_tomorrow[channel][0].title:
                shows_today[channel].pop()
        except:
            pass
        shows[channel] = shows_today[channel] + shows_tomorrow[channel]
        for show_num in range(len(shows[channel])):
            try:
                shows[channel][show_num].ending_time = shows[channel][show_num + 1].starting_time
            except IndexError:
                continue

    # Remove shows that are less than an hour long, have already finished, or lack an IMDB link:
    for channel in shows:
        shows_to_keep = []
        for show in shows[channel]:
            try:
                if (
                        show.ending_time > now and
                        show.get_length() > one_hour and
                        show.is_movie() and
                        show.starting_time < six_AM_tomorrow()
                ):
                    shows_to_keep.append(show)
            except:
                pass
            shows[channel] = shows_to_keep

    return shows

def get_shows(folder, forcefetch):
    # If folder doesn't exist, create it
    if not( folder in os.listdir('.') and os.path.isdir(folder)):
        os.mkdir(folder)
    
    # Is there a .pickle file in the specified folder?
    
    pickles = [filename for filename in os.listdir(os.path.join('.', folder)) if ".pickle" in filename]
    today = str(dt.datetime.now().date())
    
    if len(pickles) > 0 and not forcefetch:
        picklefile = pickles[0]
        picklepath = os.path.join('.', folder, picklefile)
        
        # If exists, is it from today?
        if today in picklefile:
            # If exists and from today, load it.
            picklefile = open(picklepath, 'r')
            return pickle.load(picklefile)
            
        else:
            # If exists but not from today, delete it and start again
            os.remove(picklepath)
            return get_pickled_shows(folder)
            
    else:
        # If it doesn't exist, make it and continue
        shows = fetch_content()
        picklename = os.path.join(folder, 'shows' + today + '.pickle')
        picklefile = open(picklename, 'w')
        pickle.dump(shows,picklefile)
        return shows

if __name__ == '__main__':
    forcefetch = True if any('fetch' in arg for arg in sys.argv) else False
    shows = get_shows('movies2nite_pickle', forcefetch)
    print "\nThese are probably mostly films:"
    print "=" * 32 + "\n"
    for channel in shows:
        for show in shows[channel]:
            if show.ending_time > now:
                print show
