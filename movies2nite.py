#!/usr/bin/env python
'''
Returns a list of movies on free-to-air TV in Melbourne tonight.
The info is retrieved from 'https://www.yourtv.com.au/guide/'.

Movies are identified by their length (longer than 1 hour) and the 
presence of an IMDB tag in their description. This is not perfect, 
but doesn't appear to miss movies, it just leads to false positives.

Films that have already finished are not shown.
'''

# To-do:
# - Get stuff from pre-6am the next day as well
# - Checking for an IMBD link isn't reliable. Includes a few false positives.

import urllib2, re
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
        output = "%s\t(%s - %s)\t- '%s'" % (
            self.channel,
            start_time_str,
            end_time_str,
            self.title
        )
        return hp.unescape(output)

    def get_length(self):
        try:
            return self.ending_time - self.starting_time
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

print("Please wait...")

# Get the page:
page_content = urllib2.urlopen('https://www.yourtv.com.au/guide/').read()

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
            show_time = dt.datetime(now.year, now.month, now.day, show_hour, show_minute)
            show_link = re.sub('.*href="(.*) data-event-id.*','\\1',show,1)
            show_link = re.sub('[\s+]','',show_link).split('"')[1]
            shows[channel_name].append(
                Show(text_in_element(show,'<h4>'), show_time, channel_name, show_link)
            )
        except:
            continue

# Add end times to shows
for channel in shows:
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
            if show.ending_time > now and show.get_length() > one_hour and show.is_movie():
                shows_to_keep.append(show)
        except:
            pass
    shows[channel] = shows_to_keep


# Display them:

if __name__ == '__main__':
    print "\nThese are probably mostly films:"
    print "=" * 32 + "\n"
    for channel in shows:
        for show in shows[channel]:
            print show
