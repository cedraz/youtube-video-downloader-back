from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp as youtube_dl
import os
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI()

origins = [
    "http://localhost:3000",  # Adicione a origem do seu frontend aqui
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/downloads", StaticFiles(directory="./downloads"), name="downloads")

async def delete_file_after_delay(file_path: str, delay: int):
        await asyncio.sleep(delay)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"File deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting file: {file_path}, Error: {e}")

def schedule_file_deletion(file_path, delay):
    asyncio.create_task(delete_file_after_delay(file_path, delay))

def download_video(url, path_to_save, file_format, resolution='1080p'):
    if (file_format == 'mp3'):

        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'video')
            thumbnail = info_dict.get('thumbnail', None)

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(path_to_save, f'{title}_audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }]
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return {
            'url': f'http://localhost:8000/downloads/{title}_audio.mp3', 
            'path': os.path.join(path_to_save, f'{title}_audio.mp3'),
            'thumbnail': thumbnail,
            'title': title   
        }
    
    else:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            title = info_dict.get('title', 'video')
            thumbnail = info_dict.get('thumbnail', None)

        format_string = f'bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]'
        
        ydl_opts = {
            'format': format_string,
            'outtmpl': os.path.join(path_to_save, f'{title}_{resolution}.mp4'),
            'merge_output_format': 'mp4'
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return {
            'url': f'http://localhost:8000/downloads/{title}_{resolution}.mp4',
            'path': os.path.join(path_to_save, f'{title}_{resolution}.mp4'),
            'thumbnail': thumbnail,
            'title': title,
        }

class DownloadRequest(BaseModel):
    url: str
    file_format: str
    resolution: str

@app.post("/download")
async def download(downloadRequest: DownloadRequest):
    path = "./downloads"

    if not os.path.exists(path):
        os.makedirs(path)

    if (downloadRequest.file_format == 'mp3'):
        audio = download_video(downloadRequest.url, path, 'mp3')

        if not os.path.isfile(audio['path']):
            return JSONResponse(content={"message": "Error downloading audio"}, status_code=500)
        
        schedule_file_deletion(audio['path'], 5)
        return JSONResponse(content={"url": audio['url']}, status_code=200)

    if (downloadRequest.file_format == 'mp4'):
        video = download_video(downloadRequest.url, path, 'mp4', downloadRequest.resolution)

        if not os.path.isfile(video['path']):
            return JSONResponse(content={"message": "Error downloading video"}, status_code=500)
        
        schedule_file_deletion(video['path'], 5)
        return JSONResponse(content={"url": video['url']}, status_code=200)
    
    return JSONResponse(content={"message": "Invalid file format"}, status_code=400)

@app.get("/video-info/{videoId}")
async def video_info(videoId: str):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(f'https://www.youtube.com/watch?v={videoId}', download=False)
        title = info_dict.get('title', 'video')
        thumbnail = info_dict.get('thumbnail', None)

    return JSONResponse(content={"title": title, "thumbnail": thumbnail}, status_code=200)
