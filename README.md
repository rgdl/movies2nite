# movies2nite

Returns a list of movies on free-to-air TV in Melbourne tonight.
The info is retrieved from 'https://www.yourtv.com.au/guide/'.

Movies are identified by their length (longer than 1 hour) and the 
presence of an IMDB tag in their description. This is not perfect, 
but doesn't appear to miss movies, it just leads to false positives.

Films that have already finished are not shown.

Note: checks for a pickle file in a particular folder. If there's some
unrelated pickle file in that folder, the program will get confused.

# To-do:
# - Checking for an IMBD link isn't reliable. Includes a few false positives.

