import os

from django.core.management.base import BaseCommand, CommandError

import googleapiclient.discovery
import googleapiclient.errors


class Command(BaseCommand):
    """
    Get details of the videos corresponding to the provided playlist.
    """
    def add_arguments(self, parser):
        parser.add_argument('--playlist-id', type=str, required=True)

    def handle(self, *args, **options):
        # Setup the API client
        playlist_id = options['playlist_id']
        api_service_name = "youtube"
        api_version = "v3"
        api_key = os.getenv("GOOGLE_API_KEY")

        youtube_client = googleapiclient.discovery.build(
            serviceName=api_service_name,
            version=api_version,
            developerKey=api_key,
        )

        # Fetch the video data from the API
        playlist_items = []
        items_per_page = 50  # max allowed by the api
        default_request_args = dict(
            part="snippet,contentDetails",
            maxResults=items_per_page,
            playlistId=playlist_id,
        )

        request = youtube_client.playlistItems().list(**default_request_args)
        response = request.execute()

        page_count = 1
        total_results = response["pageInfo"]["totalResults"]
        playlist_items += response["items"]

        while page_count * items_per_page < total_results:
            next_page_token = response["nextPageToken"]

            request = youtube_client.playlistItems().list(**default_request_args, pageToken=next_page_token)
            response = request.execute()

            page_count += 1
            playlist_items += response["items"]

        # Process the results
        processed_items = []
        for item in playlist_items:
            video_id = item['contentDetails']['videoId']
            youtube_title = item['snippet']['title']
            title_separator = ' - '
            title_separator_ix = youtube_title.find(title_separator)

            processed_items.append({
                'speaker': youtube_title[:title_separator_ix],
                'title': youtube_title[title_separator_ix + len(title_separator):],
                'url': f'https://www.youtube.com/watch?v={video_id}',
            })

        print(processed_items)
