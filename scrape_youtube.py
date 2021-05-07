from __future__ import unicode_literals
from pyppeteer import launch
import youtube_dl
import asyncio
import urllib.parse
import os
import sys

youtube_search_query = " ".join(sys.argv[1:]) or "music jam"
youtube_search_opts = {
  "q": urllib.parse.quote_plus(youtube_search_query),
  "sp": 'CAISBhABGAEwAQ%253D%253D' # Video, under 4 min, Creative Commons, Sort by Upload date
  # "sp": 'EgQQARgB' # Video, Under 4 min, Sort by Relevance
  # "sp": 'CAISBBABGAE%253D' # Video, Under 4 min, Sort by Upload date
}
youtube_url = "https://www.youtube.com/results?search_query=%(q)s&sp=%(sp)s" % youtube_search_opts
print(youtube_url)

skip_forward_to_video = 0

dir_path = os.path.dirname(os.path.realpath(__file__))
youtube_dl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': dir_path + '/downloads/' + youtube_search_query + '/%(title)s - (id %(id)s).%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

async def main():
  print("Open youtube downloader")
  with youtube_dl.YoutubeDL(youtube_dl_opts) as ydl:
    print("Browse to youtube")
    browser = await launch({"headless": True, "args": ['--disable-dev-shm-usage']})
    page = await browser.newPage()
    response = await page.goto(youtube_url)
    await page.setViewport({ "width": 1200, "height": 1200 })
    
    if (response.request.redirectChain):
      print("Consent to cookies")
      await asyncio.sleep(2)
      await page.evaluate('''
        () => {
          Array.from(document.querySelectorAll('span'))
            .find(el => ["I agree", "Jag godkänner"].includes(el.textContent))
            .click();
        }
      ''')

    # Wait for first video element to load, then a little more
    await page.waitForSelector('ytd-video-renderer') 
    await asyncio.sleep(1)

    last_url = None
    scroll_count = 0
    download_errors = 0
    video_count = 0
    
    while True:
      video_urls = await page.evaluate('''
        () => {
          return Array.from(document.getElementsByTagName('ytd-video-renderer'))
            .map(element => element.querySelector('a').getAttribute('href'))
            .map(href => 'https://www.youtube.com' + href)
        }
      ''')
      
      # Make sure we only consider new video urls
      if last_url and last_url in video_urls:
        last_index = video_urls.index(last_url)
        video_urls = video_urls[last_index:]

      print("Page count: {} ({} errors) | Video count: {} | Will download: {}".format(scroll_count, download_errors, video_count, len(video_urls)))

      for video_url in video_urls:
        if not skip_forward_to_video or skip_forward_to_video < video_count:
          try:
            ydl.download([video_url])
          except youtube_dl.utils.DownloadError as err:
            print("Download error: {}".format(err))
            download_errors += 1
          except:
            print("Unknown error when downloading")
            download_errors += 1

        video_count += 1

      scroll_count += 1
      last_url = video_urls[-1]

      await scrollDown(page)


async def scrollDown(page):
  await page.evaluate('''
    async () => {
      await new Promise((resolve, reject) => {
            var totalHeight = 0;
            var distance = 1000;
            var timer = setInterval(() => {
                var scrollHeight = document.body.scrollHeight;
                window.scrollBy(0, distance);
                totalHeight += distance;

                if(totalHeight >= scrollHeight){
                    clearInterval(timer);
                    resolve();
                }
            }, 100);
        });
    }
  ''')

asyncio.get_event_loop().run_until_complete(main())