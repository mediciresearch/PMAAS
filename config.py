# local text database file that ensures no duplicate videos get processed.
database = 'database.txt'

youtube = {
    'tags': '',
    'category': 28,  # has to be an int, more about category below
    'status': 'public'  # {public, private, unlisted}
}
# Note that by default, public isn't available unless you go through an audit. Checkout: https://support.google.com/youtube/contact/yt_api_form

video = {
    # (horizontal, vertical) or None (not a string but literal) to upload the original clip as is.
    'dimensions': (1080, 1920),
    'blur': False  # blur non-perfect-fit clip
}

# for category: has to be an int, refer to YouTube Data 4 API's documentation, but as of Jan 2022,
# checkout https://techpostplus.com/youtube-video-categories-list-faqs-and-solutions/
