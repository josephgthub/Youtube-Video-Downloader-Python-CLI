import os
import subprocess
import pandas as pd
import shutil
import json
import xml.etree.ElementTree as ET
import requests 
import re
import urllib.parse
import sys


def get_yt_dlp_executable():
    env_path = os.environ.get("YTDLP_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    if os.name == "nt":
        return "yt-dlp.exe"

    return "yt-dlp"


def get_download_root():
    if os.name == "nt":
        import winreg
        from pathlib import Path
        sub_key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                location, _ = winreg.QueryValueEx(key, downloads_guid)
                return location
        except Exception:
            return str(Path.home() / "Downloads")
    else:
        xdg_bin = shutil.which('xdg-user-dir')
        if xdg_bin:
            result = subprocess.run([xdg_bin, 'DOWNLOAD'], capture_output=True, text=True)
            downloads_path = result.stdout.strip()
            if downloads_path:
                return downloads_path
        return os.path.join(os.path.expanduser("~"), "Downloads")

def extract_caption_link(metadata, lang="en", ext="srv3"):
    try:
        return next((caption["url"] for caption in metadata["automatic_captions"][lang] if caption["ext"] == ext), None)
    except (KeyError, TypeError):
        return None


def sanitize_filename(filename):
    # Dictionary of restricted characters and their fullwidth replacements
    replacements = {
        '\\': '＼',  # Fullwidth backslash
        '/': '／',   # Fullwidth slash
        ':': '：',   # Fullwidth colon
        '*': '＊',   # Fullwidth asterisk
        '?': '？',   # Fullwidth question mark
        '"': '＂',   # Fullwidth double quote
        '<': '＜',   # Fullwidth less-than sign
        '>': '＞',   # Fullwidth greater-than sign
        '|': '｜',   # Fullwidth vertical bar
    }
    
    # Replace each restricted character with its fullwidth counterpart
    for char, fullwidth in replacements.items():
        filename = filename.replace(char, fullwidth)
    
    return filename


def setwords(text_parts,timestamps):
   while len(text_parts)!=len(timestamps):
    diffs=[]
    for i in range(len(timestamps)-1):
       diffs.append(timestamps[i+1]-timestamps[i])
    index=diffs.index(min(diffs))
    temptext_parts=[]
    j=0
    while j<len(text_parts):
     if j == index:
         temptext_parts.append(text_parts[j] + " " + text_parts[j+1])
         j+=2 # skip next iteration
         continue  # explicitly skip the next iteration
     else:
         temptext_parts.append(text_parts[j])
     j+=1
    text_parts=temptext_parts
   return text_parts


def convert_to_srt(xml_data,metadata):
    # Parse the XML data
    root = ET.fromstring(xml_data)
    
    # Initialize variables to store the SRT formatted output
    srt_output = []
    srt_output.append("[Script Info]")
    srt_output.append("; This is an Advanced Sub Station Alpha v4+ script.")
    srt_output.append("Title:")
    srt_output.append("ScriptType: v4.00+")
    srt_output.append("PlayDepth: 0")
    srt_output.append("ScaledBorderAndShadow: Yes")
    srt_output.append("")
    srt_output.append("[V4+ Styles]")
    srt_output.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
    if metadata.get('aspect_ratio', None):
     if metadata.get('aspect_ratio', None)<1:
      srt_output.append("Style: Default,Arial,8,&H00FFFFFF,&H0000FFFF,&H6F000000,&HA0000000,0,0,0,0,100.0,100,0.0,0,3,0.1,0.0,1,20,10,250,1")
     else:
      srt_output.append("Style: Default,Arial,13,&H00FFFFFF,&H0000FFFF,&H6F000000,&HA0000000,0,0,0,0,100.0,100,0.0,0,3,0.1,0.0,1,100,10,25,1")
    else:
      srt_output.append("Style: Default,Arial,13,&H00FFFFFF,&H0000FFFF,&H6F000000,&HA0000000,0,0,0,0,100.0,100,0.0,0,3,0.1,0.0,1,100,10,25,1")
    srt_output.append("")
    srt_output.append("[Events]")
    srt_output.append("Format: Marked, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

    counter = 1  # Start the SRT numbering from 1
    
    # Loop through each <p> element which contains the paragraphs
    forskip=0
    find=root.findall(".//p")
    prevscentence=""
    prevnoappend=""
    for p_element in find:
        forskip=forskip+1
        t = int(p_element.get("t"))  # Start time of the paragraph
        d = p_element.get("d")  # Duration of the paragraph
        
        if d is None:
            continue  # Skip processing if there's no duration
        
        d = int(d)  # Convert the duration to integer
        text_parts = []  # List to hold the words
        
        # Check if there are <s> elements within the current <p> element
        s_elements = p_element.findall(".//s")
        
        if s_elements:
            # If there are <s> elements (words), process each word
            for s_element in s_elements:
              if s_element.text!=None:
                try:
                    word = s_element.text.encode('windows-1252').decode('utf-8')
                except Exception as e:
                    word=s_element.text
                if word:
                   word = word.strip()
                   word = word.encode('utf-8').decode('utf-8')
                   text_parts.append(word)
                elif s_element.text== '\n':  # If the text is exactly a newline, append it
                    text_parts.append('\n')

        else:
            # If there are no <s> elements, treat the <p> text as a whole
            p_text = p_element.text
            if p_text == '\n':  # If the whole text is exactly \n, append it
                text_parts.append('\n')
            elif p_text:  # Avoid appending empty text
                text_parts.append(p_text.strip())
        

        timestamps = []
        
        # Loop through each <p> element
            # Find all <s> elements inside the <p> element
        if len(find)!=forskip and find[forskip].get("d",None)!=None:
         endt=int(find[forskip].get("t"))-t
        else:
         endt=d
        if s_elements:
            # If there are <s> elements (words), process each word
            for s_element in s_elements:
                s_time = s_element.get("t") # The subtitle word
                if s_time:  # Ensure the word is not empty
                    s_time=int(s_time)
                    timestamps.append(s_time)
            timestamps.append(endt)

        else:
            # If there are no <s> elements, treat the <p> text as a whole
            timestamps.append(endt)

        if len(text_parts)>len(timestamps):
           text_parts=setwords(text_parts,timestamps)

        # Create subtitle entries
        current_time = t
        start=current_time
        prev=""
        ti=0
        wordcount=0
        for word in text_parts:
            wordcount+=1
            if repr(word) == "'\\n'" and repr(prevscentence[-1:]) == "'\\n'":
               prevscentence=""
               continue
               
            word_duration = timestamps[ti]
            end_time = start + word_duration
            # Format the SRT entry
            if wordcount%14!=0:
             if prevscentence:
              text=(prevscentence+prev+word).strip()
             else:
              text=prev+word
            else:
             if prevscentence:
              text=(prevscentence+prev+"\\N"+word).strip()
             else:
              text=prev+"\\N"+word

            srt_entry=f"Dialogue: {counter-1},{format_time_ms(current_time)},{format_time_ms(end_time)},Default,,0,0,0,,{text}"
            srt_output.append(srt_entry)
            if wordcount%14!=0:
             prev=prev+word+" "
            else:
             prev=prev+"\\N"+word+" "
            # Update the current time for the next word
            current_time=end_time
            ti=ti+1
            counter += 1
        if len(find)!=forskip and find[forskip].get("d",None)!=None:         
         prevscentence=prevnoappend.strip()+"\\N"+prev[:-1].strip()
         prevnoappend=prev[:-1].strip()
        else:
         prevscentence=""
    # Join the output list into a single string
    return "\n".join(srt_output)


def format_time_ms(ms):
    """Converts time in milliseconds to the SRT format (HH:MM:SS,MS)."""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds, milliseconds = (ms % 60000) // 1000, ms % 1000
    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"[:-1]

def save_srt_file(input_file_path, srt_data):
    srt_file_path = input_file_path
    # Write the SRT data to the output file
    with open(srt_file_path, "w", encoding="utf-8") as file:
        file.write(srt_data)    
    return srt_file_path


def download_subtitles(download_folder,metadata):
    caption_link = extract_caption_link(metadata)
    print(caption_link)
    output_file = os.path.join(download_folder, "English"+".ass")
    response = requests.get(caption_link)
    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        srt_data = convert_to_srt(response.content,metadata)
        save_srt_file(output_file, srt_data)
    else:
        print(f"Failed to download file. Status code: {response.status_code}")



def download_metadata(url):
    command = [
        get_yt_dlp_executable(),
        "--skip-download",
        "--print-json",
        "--quiet",
        url
    ]
    
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True)

    try:
        return json.loads(result.stdout)
    except Exception as e:
        print("No Metadata Found")
        return None

# def embed_subtitles_mkv(video_file, vtt_file, output_file):
#     try:
        
#         # Command to run mkvmerge
#         command = [
#             'mkvmerge', 
#             '-o', output_file,           # Output file
#             '--language', '0:eng',        # Set language of video/audio track (optional)
#             '--default-track', '0:yes',   # Set video as the default track
#             '--language', '1:eng',        # Set language of subtitle track
#             '--default-track', '1:yes',   # Set subtitle as the default track
#             video_file,                   # Input video file
#             vtt_file                      # Input subtitle file
#         ]
        
#         # Run the mkvmerge command
#         subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

#     except subprocess.CalledProcessError as e:
#         print("Cannot Merge Video And Subtitle",e)



def embed_subtitles_mkv(video_file, vtt_file, output_file):
    try:
        # FFmpeg command to mux video + subtitle into MKV
        command = [
            'ffmpeg',
            '-i', video_file,               # Input video
            '-i', vtt_file,                 # Input subtitle
            '-map', '0',                    # Map all video/audio tracks from the video file
            '-map', '1',                    # Map the subtitle file
            '-c', 'copy',                   # No re-encode (fast)
            '-metadata:s:s:0', 'language=eng',     # Subtitle language
            '-disposition:s:0', 'default',         # Make subtitle default
            output_file
        ]

        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    except subprocess.CalledProcessError as e:
        print("Cannot Merge Video And Subtitle", e)




def embed_subtitles_in_folder(folder_path):
    # List all files in the folder
    files = os.listdir(folder_path)
    
    # Filter for the video file and subtitle file (assumes only one of each)
    video_file = None
    vtt_file = None
    
    for file in files:
        if file.endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.mpeg', '.mpg')):
         video_file = os.path.join(folder_path, file)
         new_video_name = os.path.join(folder_path, 'temp' + os.path.splitext(file)[1])  # Retains the original file extension
         os.rename(video_file, new_video_name)
        
        elif file.endswith('.ass'):
          vtt_file = os.path.join(folder_path, file)
          new_vtt_name = os.path.join(folder_path, 'temp.ass')  # Renaming the subtitle file to temp.ass
          os.rename(vtt_file, new_vtt_name)

    # Ensure both video and subtitle files are found
    if video_file and vtt_file:
        # Construct the output file path with the original video name (keeping the same extension)
        output_file = os.path.join(folder_path, os.path.basename(video_file))  # Same name as original video
        
        embed_subtitles_mkv(new_video_name, new_vtt_name, output_file)
        # Delete the original video and subtitle files after embedding subtitles
        os.remove(new_video_name)
        os.remove(new_vtt_name)




def edit_vtt(a):
  flag=False
  first=False
  for i in range(len(a)-1,0,-1):
      if a[i]=="." and first==False:
          first=i
      elif a[i]=="." and first!=False:
          start=i
          flag=True
          break
  if flag:
      a=a[:start] + a[first:]
      a=a.replace(".mp3","")
      a=a.replace(".mp4","")
  return a

import subprocess

def convert_to_mp3(input_file, output_file):
    # Command to convert the file using FFmpeg
    command = [
        'ffmpeg',
        '-i', input_file,   # Input file
        '-vn',               # No video (only audio)
        '-ar', '44100',      # Set audio sample rate (optional)
        '-ac', '2',          # Set audio channels to stereo (optional)
        '-b:a', '192k',      # Set bitrate (optional)
        output_file          # Output file
    ]
    
    # Run the command without printing anything (redirect stdout and stderr to DEVNULL)
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def update_video_file_extension(download_folder,metadata):
    l=len([f for f in os.listdir(download_folder)])
    for filename in os.listdir(download_folder):
      os.rename(os.path.join(download_folder, filename),os.path.join(download_folder, sanitize_filename(metadata["title"])+os.path.splitext(filename)[1].lower()))
    if l==2:
     for filename in os.listdir(download_folder):
        valid_video_extensions = ['.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv']
        old_file_path = os.path.join(download_folder, filename)
        if os.path.isfile(old_file_path):
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension == ".mp3":
                temp="temp.mp3"
                os.rename(os.path.join(download_folder, filename), os.path.join(download_folder, temp))
                output=os.path.join(download_folder, filename)
                input=os.path.join(download_folder, temp)
                convert_to_mp3(input, output)
                os.remove(input)
                new_filename=filename
            elif file_extension == ".ass":
                new_filename = edit_vtt(filename)
            elif file_extension == ".srt":
                new_filename = edit_vtt(filename)
            elif file_extension not in valid_video_extensions :
                new_filename = filename + '.mkv'
                file_extension=".mkv"
            else:
                if file_extension != '.mkv':
                    new_filename = filename.replace(file_extension, '.mkv')
                    file_extension=".mkv"
                else:
                    new_filename=filename.replace(file_extension, '.mkv')
                    pass  # No need to do anything if it's already .mkv
            new_file_path = os.path.join(download_folder, new_filename)
            os.rename(old_file_path, new_file_path)
     embed_subtitles_in_folder(download_folder)           
    for filename in os.listdir(download_folder):
        valid_video_extensions = ['.mp4', '.mkv', '.webm', '.mov', '.avi', '.flv', '.wmv']
        old_file_path = os.path.join(download_folder, filename)
        if os.path.isfile(old_file_path):
            file_extension = os.path.splitext(filename)[1].lower()
            if file_extension == ".mp3":
                temp="temp.mp3"
                os.rename(os.path.join(download_folder, filename), os.path.join(download_folder, temp))
                output=os.path.join(download_folder, filename)
                input=os.path.join(download_folder, temp)
                convert_to_mp3(input, output)
                os.remove(input)
                new_filename=filename
            elif file_extension == ".ass":
                new_filename = edit_vtt(filename)
            elif file_extension == ".srt":
                new_filename = edit_vtt(filename)
            elif file_extension not in valid_video_extensions :
                new_filename = filename + '.mkv'
                file_extension=".mkv"
            else:
                if file_extension != '.mkv':
                    new_filename = filename.replace(file_extension, '.mkv')
                    file_extension=".mkv"
                else:
                    new_filename=filename.replace(file_extension, '.mkv')
                    pass  # No need to do anything if it's already .mkv
            new_file_path = os.path.join(download_folder, new_filename)
            
            os.rename(old_file_path, new_file_path)

            parent_folder = os.path.dirname(download_folder)
            
            old_file_path = new_file_path

            if os.path.isfile(old_file_path):
                new_filename= os.path.basename(new_file_path)
                namelen=len(os.path.splitext(new_filename)[0].lower())
                if new_filename in os.listdir(parent_folder):
                    new_filename = new_filename.replace(file_extension, f' ({1}){file_extension}')
                    i = 2
                    while new_filename in os.listdir(parent_folder):
                        new_filename = new_filename.replace(new_filename[namelen:], f' ({i}){file_extension}')
                        i += 1
                new_file_path = os.path.join(download_folder, new_filename)
                os.rename(old_file_path, new_file_path)
            
            source_path = os.path.join(download_folder, new_filename)
            destination_path = os.path.join(parent_folder, new_filename)
            shutil.move(source_path, destination_path)
    shutil.rmtree(download_folder) 


def create_unique_folder(path):
        if not os.path.exists(path):
            os.makedirs(path)
            return path
        else:
            i = 1
            while os.path.exists(path + f" ({i})"):
                i += 1
            new_folder_path = path + f" ({i})"
            os.makedirs(new_folder_path)
            return new_folder_path


def humanized(bytes_size):
    if bytes_size is None or bytes_size <= 0:
        return 'N/A'
    units = [' B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    size = float(bytes_size)
    for unit in units:
        if size < 1000:
            return f"{round(float(size),2):.2f} {unit}"
        size /= 1024

def get_all_available_formats(url):
    command = [
        get_yt_dlp_executable(),
        "-F",
        url
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    formats = []
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            formats.append(output.strip())
        
    return formats


def get_available_formats(metadata):
        audiosize = ([f for f in metadata['formats'] if f.get('audio_ext') != 'none'][-1].get('filesize') or [f for f in metadata['formats'] if f.get('audio_ext') != 'none'][-1].get('filesize_approx'))
        try:
            duration = metadata.get('duration', None)
            video_info = metadata
            formats = video_info.get('formats', [])
            formats_list = []

            for f in formats:
                if str(f.get('format_note', 'N/A')).lower() == "premium":
                    bitrate = f.get('tbr', 0)
                    url = f.get('url', '')

                    # Step 1: Decode the URL
                    decoded_url = urllib.parse.unquote(url)

                    # Step 2: Extract 'clen' value from the decoded URL
                    clen_match = re.search(r'clen=(\d+)', decoded_url)
                    file_size = int(clen_match.group(1)) if clen_match else 0

                    # Add audio size if necessary
                    if file_size and audiosize:
                        file_size += audiosize

                    formats_list.append({
                        'ID': f.get('format_id', 'N/A'),
                        'Resolution': f.get('resolution', 'N/A'),
                        'FileSize': humanized(file_size) if file_size else "Unknown",
                        'Bit Rate': str(round(float(bitrate))) + "k" if isinstance(bitrate, (int, float)) else 'N/A',
                        'Quality': str(f.get('format_note', 'N/A'))
                    })
                    break
                file_size = f.get('filesize', 0)
                index = 0
                flag = True
                for q in formats_list:
                    if f.get('filesize', None) is None:
                        break
                    elif q.get('Quality') == str(f.get('format_note', 'N/A')) and str(f.get('format_note', 'N/A')) + "p" != "Nonep" and str(f.get('format_note', 'N/A')) + "p" != "N/Ap":
                        size_units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
                        
                        def to_bytes(size):
                            value, unit = size[:-2], size[-2:]
                            value = float(value)  # Convert value to float
                            unit = unit.upper()  # Convert unit to uppercase for consistency
                            return value * size_units[unit]
                        
                        size1_bytes = to_bytes(humanized(file_size))
                        size2_bytes = to_bytes(q.get('FileSize'))

                        if size1_bytes == size2_bytes:
                            flag = False
                            break
                        elif size1_bytes < size2_bytes:
                            flag = False
                            break
                        else:
                            formats_list[index]["ID"] = f.get('format_id', 'N/A')
                            formats_list[index]["Resolution"] = f.get('resolution', 'N/A')
                            formats_list[index]["FileSize"] = humanized(file_size) if file_size else "Unknown"
                            formats_list[index]["Bit Rate"] = str(round(float(f.get('tbr', 0)))) + "k" if isinstance(f.get('tbr', 0), (int, float)) else 'N/A'
                            formats_list[index]["Quality"] = str(f.get('format_note', 'N/A'))
                            flag = False
                            break
                    index += 1

                if flag:
                    if f.get('filesize', None) is None or str(f.get('height', 'N/A')) + "p" == "Nonep":
                        continue
                    else:
                        formats_list.append({
                            'ID': f.get('format_id', 'N/A'),
                            'Resolution': f.get('resolution', 'N/A'),
                            'FileSize': humanized(file_size) if file_size else "Unknown",
                            'Bit Rate': str(round(float(f.get('tbr', 0)))) + "k" if isinstance(f.get('tbr', 0), (int, float)) else 'N/A',
                            'Quality': str(f.get('format_note', 'N/A'))
                        })

            df = pd.DataFrame(formats_list)

            return df
        except Exception:
            if os.path.exists(download_folder):
                shutil.rmtree(download_folder)  # This will delete the folder and its contents
            return None


def ensure_download_folder_exists(download_folder):
    if not os.path.exists(download_folder):
        print(f"The folder '{download_folder}' does not exist. Creating it now...")
        os.makedirs(download_folder)


def download_video_with_subtitles(url,download_folder,metadata):
    ensure_download_folder_exists(download_folder)

    d = input("1: Audio\n2: Video (All Formats)\n3: Video (Important Formats)\nEnter Your Choice: ")
    try:
     output_file = os.path.join(download_folder, sanitize_filename(metadata["title"]))
    except:
     output_file = os.path.join(download_folder, "Unknown")

    if d == "1":
        command = [
            get_yt_dlp_executable(),
            "-o", os.path.join(download_folder, "%(title)s.%(ext)s.mp3"),
            "-f", 'bestaudio/best',
            url
        ]

        
        try:
            print("The Download is about to start...")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    if '[download]' in output and 'Destination:' not in output:
                        print("\r" + output.strip(), end='                  ', flush=True)
            stderr_output = process.stderr.read()
            if stderr_output:
                print(f"\nError: {stderr_output}")
            update_video_file_extension(download_folder,metadata)
            print(f"\nDownload complete!")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

    else:
        selectedformat=None
        if d=="2":
          formats=get_all_available_formats(url)
          print("\nAvailable formats:")
          for format_info in formats:
              print(format_info)
          selectedformat = input("\nEnter the format code you want to download (e.g., 137 for 1080p): ")
          
        else:
           df = get_available_formats(metadata)
           if df is None:
            print("There are no Valid Formats Available\n")
            selectedformat="xqbq" #random
           else:
               formats = [df.columns.tolist()] + df.values.tolist()
               print("\nAvailable formats:")
               print(df)


               selectedformat = input("\nEnter the format code you want to download (e.g., 137 for 1080p): ")
               

               id_list = df['ID'].tolist()
               if selectedformat=="":
                 if os.path.exists(download_folder):
                   shutil.rmtree(download_folder)
                   pass
               elif selectedformat not in id_list:
                   preferred_resolutions = ["Premium","1080p60","720p60","1080p",'720p', '480p', '360p', '240p', '144p']
                   selectedformat = None
                   for resolution in preferred_resolutions:
                       for format_info in formats:
                           if resolution in format_info:
                               selectedformat = format_info[0]
                               break
                       if selectedformat:
                           break
                   else:
                       selectedformat = formats[-1][0]
                       print(f"Selected format: {selectedformat}")

        if selectedformat:       
            selected_formats = [x.strip() for x in selectedformat.replace(',', ' ').split()]
            lang="en"
            if lang in metadata["automatic_captions"]:
                if any(c.get("ext") == "srv3" for c in metadata["automatic_captions"][lang]): download_subtitles(download_folder, metadata)
            for m, selected_format in enumerate(selected_formats, 1):
                command = [
                       get_yt_dlp_executable(), 
                       "-o", os.path.join(download_folder, "%(title)s.%(ext)s"), 
                       "-f", f"{selected_format}+bestaudio/best",
                       url
                   ]



                try:
                    print(f"\n{m}: The Download is about to start...\nQuality={selected_format}")
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            if '[download]' in output and 'Destination:' not in output:
                                print("\r" + output.strip(), end='                     ', flush=True)
                    stderr_output = process.stderr.read()
                    if stderr_output:
                        print(f"\nError: {stderr_output}")
                    update_video_file_extension(download_folder,metadata)
                    print(f"\nDownload complete!\n")

                except Exception as e:
                    print(f"An error occurred{e}")
        
        

    video_url = input("\nEnter the Video URL: ")
    if video_url:
                metadata=download_metadata(video_url)
                try:
                        name = "temp"
                        folder_path = os.path.join(get_download_root(), name)
                        download_folder=create_unique_folder(folder_path)
                        download_video_with_subtitles(video_url,download_folder,metadata)
                except KeyboardInterrupt as e:
                        print("\nExiting...")
                finally:
                        if os.path.exists(download_folder):
                                shutil.rmtree(download_folder) 


if __name__ == "__main__":
  print("Downloader with Quality Options\n")
  video_url = input("Enter the Video URL: ")
  if video_url:
    metadata=download_metadata(video_url)
    try:    
        name = "temp"
        folder_path = os.path.join(get_download_root(), name)
        download_folder=create_unique_folder(folder_path)
        download_video_with_subtitles(video_url,download_folder,metadata)
    except KeyboardInterrupt as e:
        print("\nExiting...")
    finally:
        if os.path.exists(download_folder):
            shutil.rmtree(download_folder)
