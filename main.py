import subprocess
import re
import asyncio
import os
import json
from datetime import datetime, timedelta
from openai import AsyncOpenAI

input_file = 'videoplayback.mp4'
output_file = 'output.mp4'
transcript = 'transcript.txt'

file_path = 'segments.json'
OPEN_AI_API_KEY = os.environ['OPEN_AI_API']

data = [{
    "start_time":
    "0:00",
    "end_time":
    "0:35",
    "entire_segment_text":
    "World leaders, particularly America and China, are taking AI seriously. Biden and Xi Jinping have already held talks about it. The fact that these world powers are discussing AI is promising. The UN Secretary General even mentioned that he's open to creating an international body for AI research. This cooperation could create a strong foundation for global AI governance.",
    "0:00":
    "World leaders, particularly America and China, are taking AI seriously.",
    "0:06":
    "Biden and Xi Jinping have already held talks about it.",
    "0:12":
    "The fact that these world powers are discussing AI is promising.",
    "0:19":
    "The UN Secretary General even mentioned that he's open to creating an international body for AI research.",
    "0:26":
    "This cooperation could create a strong foundation for global AI governance."
}, {
    "start_time": "5:00",
    "end_time": "5:35",
    "entire_segment_text":
    "A recent study involving 2,700 AI researchers predicted job automation by 2100. However, that doesn't align with the rapid advancements we're witnessing. Job automation is likely to come much sooner than anticipated. People like us are crucial to share this knowledge on platforms like YouTube. Having an optimistic outlook on AI is rare but necessary.",
    "5:00":
    "A recent study involving 2,700 AI researchers predicted job automation by 2100.",
    "5:06":
    "However, that doesn't align with the rapid advancements we're witnessing.",
    "5:11": "Job automation is likely to come much sooner than anticipated.",
    "5:17":
    "People like us are crucial to share this knowledge on platforms like YouTube.",
    "5:23": "Having an optimistic outlook on AI is rare but necessary."
}, {
    "start_time":
    "10:01",
    "end_time":
    "10:37",
    "entire_segment_text":
    "Mustafa Suleyman was asked if AI could take over humanity. He decisively shut down that idea, stating there is no likelihood of such an outcome. This contradicts the common fear many have about AI. His assurance is significant coming from someone behind major AI advancements. It's encouraging to see industry leaders aligning with a positive view on AI's future.",
    "10:01":
    "Mustafa Suleyman was asked if AI could take over humanity.",
    "10:07":
    "He decisively shut down that idea, stating there is no likelihood of such an outcome.",
    "10:13":
    "This contradicts the common fear many have about AI.",
    "10:19":
    "His assurance is significant coming from someone behind major AI advancements.",
    "10:26":
    "It's encouraging to see industry leaders aligning with a positive view on AI's future."
}]


async def analyse_transcript(transcript) -> None:

    client = AsyncOpenAI(api_key=OPEN_AI_API_KEY)
    input_text = ""
    with open(transcript, 'r') as file:
        contents = file.read()
        input_text = contents

    instructions = "You are a video editor. You will search a video transcript and find part(s) suitable for the content of YouTube Shorts, which are quick videos (between 30 and 60 seconds) that communicate a single strong or provocative idea. Each segment should have at least 5 lines of text. Please respond with a JSON array where each element is an object containing the start time, end time, and exact segment text, followed by a list of each segment's individual lines of text, in this format:[{\"start_time\": \"min:sec\",\"end_time\": \"min:sec\",\"entire_segment_text\": \"...\", \"min:sec\":\"line_text\"},] .. please no leading or trailing backticks or other formatting ... The transcript is as follows: " + input_text
    try:
        chat_completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": instructions
            }],
        )

        response_content = chat_completion.choices[0].message.content
        print(response_content)
        # may be redundant, but probably harmless to keep
        cleaned_response = response_content.strip()
        print("cleaned_response:", cleaned_response)
        segments = json.loads(response_content)
        with open(file_path, 'w') as json_file:
            json.dump(segments, json_file, indent=4)
        print(f"JSON data successfully written to {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_transcript(transcript_text):
    """Parses the transcript into a list of tuples containing (timestamp, text)."""
    pattern = r'(\d{1,2}:\d{2})\n(.+?)\n(?=\d{1,2}:\d{2}|$)'
    matches = re.findall(pattern, transcript_text, re.DOTALL)
    return [(timestamp, text.replace('\n', ' ').strip())
            for timestamp, text in matches]


def convert_time_format(time_str):
    """Converts MM:SS or H:MM:SS to H:MM:SS,MS format for SRT."""
    parts = time_str.split(':')
    if len(parts) == 2:  # MM:SS
        parts = ['00'] + parts
    return f"{parts[0]}:{parts[1]}:{parts[2]},000"


def generate_srt(subtitles, output_file):
    """Generates an SRT file from the JSON data."""
    with open(output_file, 'w') as f:
        counter = 1
        for segment in subtitles:
            keys = list(segment.keys())
            for i, time in enumerate(keys):
                if time in ['start_time', 'end_time', 'entire_segment_text']:
                    continue

                start_time = convert_time_format(time)

                # Determine the end time (either the start time of the next subtitle or the segment's end time)
                if i + 1 < len(keys) and keys[i + 1] not in ['start_time', 'end_time', 'entire_segment_text']:
                    end_time = convert_time_format(keys[i + 1])
                else:
                    end_time = convert_time_format(segment['end_time'])

                f.write(f"{counter}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment[time]}\n\n")
                counter += 1


def time_to_seconds(time_str):
    """Convert a time string (MM:SS or HH:MM:SS) to seconds."""
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:  # MM:SS
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:  # HH:MM:SS
        return parts[0] * 3600 + parts[1] * 60 + parts[2]


def seconds_to_time(seconds):
    """Convert seconds to a time string (HH:MM:SS)."""
    return str(timedelta(seconds=seconds))


def adjust_times(start_time, end_time, adjustment):
    """Adjust start and end times by a given number of seconds."""
    start_seconds = time_to_seconds(start_time) - adjustment
    end_seconds = time_to_seconds(end_time) + adjustment
    if start_seconds < 0:
        start_seconds = 0
    return seconds_to_time(start_seconds), seconds_to_time(end_seconds)


def get_crop_filter(input_width, input_height):
    """Generate the crop filter to achieve a 16:9 aspect ratio."""
    original_aspect_ratio = input_width / input_height
    target_aspect_ratio = 9 / 16

    if original_aspect_ratio > target_aspect_ratio:
        # Crop width (keep height)
        new_width = int(input_height * target_aspect_ratio)
        crop_x = (input_width - new_width) // 2
        return f"crop={new_width}:{input_height}:{crop_x}:0"
    else:
        # Crop height (keep width)
        new_height = int(input_width / target_aspect_ratio)
        crop_y = (input_height - new_height) // 2
        return f"crop={input_width}:{new_height}:0:{crop_y}"


def edit_video(input_file, output_file, start_time, end_time, segment_duration, segment_number, text):
    output_file = 'output' + str(segment_number) + '.mp4'

    # Adjust times by 1 second before and after
    adjusted_start, adjusted_end = adjust_times(start_time, end_time, 1)

    # Get video dimensions
    probe_cmd = [
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
        'stream=width,height', '-of', 'csv=p=0:s=x', input_file
    ]
    result = subprocess.run(probe_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    input_width, input_height = map(int,
                                    result.stdout.decode().strip().split('x'))
    # Create crop filter for 16:9 aspect ratio
    crop_filter = get_crop_filter(input_width, input_height)

    # Apply fade and optional text overlay
    if text:
        vf_filter = f"{crop_filter},drawtext=text='{text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2,fade=t=in:st=0:d=1,fade=t=out:st={segment_duration-1}:d=1"
    else:
        vf_filter = f"{crop_filter},fade=t=in:st=0:d=1,fade=t=out:st={segment_duration-1}:d=1"

    command = [
        'ffmpeg', '-ss', adjusted_start, '-to', adjusted_end, '-i', input_file,
        '-vf', vf_filter, '-af',
        f"afade=t=in:st=0:d=1,afade=t=out:st={segment_duration-1}:d=1", '-c:v',
        'libx264', '-c:a', 'aac', output_file, '-loglevel', 'info'
    ]

    subprocess.run(command)


def create_shorts():
    video_segments = []
    with open('segments.json', 'r') as file:
        video_segments = json.load(file)

    for segment in video_segments:
        start_time = segment['start_time']
        end_time = segment['end_time']
        segment_number = video_segments.index(segment)
        segment_duration = time_to_seconds(end_time) - time_to_seconds(
            start_time)

        print(f"Start: {start_time}, End: {end_time}")
        edit_video(input_file, output_file, start_time, end_time,
                   segment_duration, segment_number, text)


def add_subtitles_to_video(input_file, output_file, srt_file):
    """Adds subtitles to the video using FFmpeg."""
    command = [
        'ffmpeg', '-i', input_file, '-vf', f"subtitles={srt_file}",
        '-c:a', 'copy', output_file, '-loglevel', 'info'
    ]
    subprocess.run(command)

# analyse transcript:
# asyncio.run(analyse_transcript(transcript))

# generate subtitles
srt_file = 'subtitles.srt'
# generate_srt(data, srt_file)

# add subtitles to video
output_file = 'output_with_subtitles.mp4'
add_subtitles_to_video(input_file, output_file, srt_file)

# create_shorts()

# edit_video(input_file, output_file, start_time, end_time, segment_number, text)
