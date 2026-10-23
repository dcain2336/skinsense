# build_film.py - turn the captured LIVE stills plus TTS narration into the SkinSense demo film.  # Module header: what this file is.
# Written 2026-10-23 for the YouCam API Skin AI & eCommerce VTO Hackathon, following the proven QuizForge recipe: one clip per shot, each timed to its narration segment, gentle motion, fades, concat, mux.  # Provenance: demo tooling, same recipe as the QuizForge Live demo.
# Honesty contract: every still comes from capture_live.py's genuine live session (mode "live", overall 74, skin age 31, priorities redness/pore/radiance, basket $150 -> $66), and the narration quotes exactly those numbers - including the honest sentence about the VTO placeholder.  # Honesty: the film says what the session did, nothing more.
# Import the JSON module so ffprobe output can be parsed.  # Library: json.
import json  # Make the json module available.
# Import the OS module for path building.  # Library: os.
import os  # Make the os module available.
# Import the subprocess module so ffmpeg, ffprobe, and the tts CLI can be run.  # Library: subprocess.
import subprocess  # All media work is delegated to these three tools.
# Define the folder this script lives in.  # Constant: script folder.
HERE = os.path.dirname(os.path.abspath(__file__))  # Absolute path of demo/.
# Define the folder holding the captured stills.  # Constant: stills folder.
SHOTS = os.path.join(HERE, "gallery")  # capture_live.py wrote the frames here.
# Define the folder that will hold the narration audio segments.  # Constant: audio folder.
AUDIO = os.path.join(HERE, "audio")  # One MP3 per narration segment.
# Define the folder that will hold the intermediate per-shot clips.  # Constant: clips folder.
CLIPS = os.path.join(HERE, "clips")  # One silent MP4 and one padded M4A per shot.
# Create the working folders if they do not exist yet.  # Step: prepare folders.
os.makedirs(AUDIO, exist_ok=True)  # Safe to re-run.
# Create the clips folder the same way.  # Step: prepare clips.
os.makedirs(CLIPS, exist_ok=True)  # Safe to re-run.
# Define the shot order and the exact narration spoken over each shot (every number verified against the captured session payload).  # Data: the demo script.
SEGMENTS = [  # One tuple per shot: (still filename, narration text).
    ("shot0-title.png", "Most skincare is bought on promises: a wall of confident claims, and no measurement. SkinSense Agent starts somewhere else - with a real A I skin analysis, and an agent that keeps listening after the first answer."),  # Title card: the problem and the premise.
    ("shot1-hero-photo.png", "You describe your skin in your own words, and add a front-facing selfie. The badge reads live-ready: the app is connected to YouCam's Skin A I, and this session is a real analysis of my own photo - not sample data."),  # Step 1 with the photo attached and the live badge on screen.
    ("shot2-live-scores.png", "Perfect Corp's engine scores eight concerns. Mine came back with redness at fifty-five, pores at sixty-six, and radiance at seventy-two as the weakest areas - an overall skin score of seventy-four, and an estimated skin age of thirty-one."),  # Step 2: the genuine live scores, quoted exactly.
    ("shot3-routine.png", "The agent ranks those concerns weakest-first and builds a morning and evening routine around them. Every card names the product, the price, and the reason it earned its place - the first treatment aims straight at redness, my weakest score."),  # Step 3: the routine scrolling from AM to the tint finishers.
    ("shot3b-tryon.png", "Tinted finishers carry a try-it-on button for YouCam's makeup virtual try-on. In this build that step is a labeled placeholder - the try-on task requires a public image U R L, and a private selfie stays private. Nothing is faked on screen."),  # Step 3b: the honest VTO state, ending on the server's own message.
    ("shot4-refine.png", "Then I push back: under twenty dollars each, and everything fragrance-free. The routine rebuilds, and the agent shows its receipt - seven changes, with every swap named, and the basket falling from a hundred and fifty dollars to sixty-six."),  # Step 4: the refine round and its change list.
    ("shot1-hero-photo.png", "Under the hood it is deliberately boring: zero-dependency Python, a deterministic agent with no L L M bill and no nondeterminism - and an honesty rule baked in. Sample data is always labeled as sample, never dressed up as a measurement."),  # How we built it, over the product reprise.
    ("shot2-live-scores.png", "For shoppers, that means a routine derived from a measurement instead of a marketing claim - with a budget the agent actually respects. For retailers, it is a storefront pattern that keeps listening after the first answer."),  # The value case, over the scores that prove it.
    ("shot0-title.png", "Describe, analyze, recommend, refine - an agent that measures, recommends, and listens. SkinSense Agent, built on the YouCam Skin A I."),  # Closing over the title card reprise.
]  # End of the demo script.
# Define the narration head/tail padding, in seconds, inside every clip.  # Constant: padding.
PAD = 0.35  # A breath before the voice starts and after it ends.
# Define the fade length, in seconds, at both ends of every clip.  # Constant: fade.
FADE = 0.35  # Short fades to black read as clean cuts in a slideshow demo.
# Define the frame rate of the finished video.  # Constant: fps.
FPS = 30  # Standard for hackathon embeds and video hosts.
# Define the frame size of the finished video.  # Constant: frame size.
FRAME_W, FRAME_H = 1280, 720  # 720p, the house standard.
# Define the pad color for short stills (the page's warm background, sampled from the UI).  # Constant: pad color.
PAD_COLOR = "0xf8f3ea"  # A warm off-white that matches the app's own background.
# Start the helper that runs a command and fails loudly on error.  # Function: run.
def run(cmd, input_text=None):  # Execute one external command, optionally feeding it stdin text.
    # Run the command, capturing its output for diagnostics.  # Step: execute.
    done = subprocess.run(cmd, input=input_text, capture_output=True, text=True)  # ffmpeg and friends report on stderr.
    # Turn any non-zero exit into an exception carrying the tail of the output.  # Step: check.
    if done.returncode != 0:  # Zero means success for all three tools.
        # Raise with the command and the useful end of its log.  # Step: raise failure.
        raise RuntimeError("Command failed: " + " ".join(cmd) + "\n" + (done.stderr or done.stdout)[-2000:])  # Keep the useful end of the log.
    # Hand back the completed process for callers that need stdout.  # Step: return.
    return done  # ffprobe results are read from here.
# Start the helper that measures a media file's duration in seconds.  # Function: duration_of.
def duration_of(path):  # Ask ffprobe how long a media file plays.
    # Run ffprobe and ask for the format duration as JSON.  # Step: probe.
    done = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path])  # Quiet, machine-readable output.
    # Parse the JSON and return the duration as a float.  # Step: read.
    return float(json.loads(done.stdout)["format"]["duration"])  # Seconds, sub-second precision.
# Start the helper that reads a still's pixel dimensions.  # Function: size_of.
def size_of(path):  # Ask ffprobe how big a still image is.
    # Run ffprobe and ask for the first stream's dimensions as JSON.  # Step: probe size.
    done = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path])  # PNG stills report one video stream.
    # Read the stream record.  # Step: read stream.
    stream = json.loads(done.stdout)["streams"][0]  # Width and height live here.
    # Return the dimensions as a pair of ints.  # Step: return size.
    return int(stream["width"]), int(stream["height"])  # The pan/pad decision uses these.
# Start the main build: narrate, time, render, concat, mux.  # Function: main.
def main():  # Produce skinsense-demo.mp4 in this folder.
    # Hold the per-segment clip durations (narration plus padding) for the render pass.  # State: durations.
    durations = []  # One float per segment, in script order.
    # Hold the spoken lines so the exact script is saved for the submission record.  # State: script lines.
    script_lines = []  # Written to narration.txt below.
    # First pass: synthesize every narration segment and measure it.  # Step: narration pass.
    for idx, (shot, text) in enumerate(SEGMENTS, start=1):  # idx is the 1-based segment number.
        # Build this segment's narration path.  # Step: name the file.
        seg_audio = os.path.join(AUDIO, f"seg{idx:02d}.mp3")  # audio/segNN.mp3.
        # Synthesize the narration only if it is not already on disk, so re-runs stay fast.  # Step: speak.
        if not os.path.exists(seg_audio):  # A kept segment is never re-voiced.
            # Call the house TTS CLI with the segment text.  # Step: synthesize.
            run(["/opt/hatch/bin/tts", "speak", "--text", text, "--output", seg_audio])  # Default voice, text passed as an argument.
        # This clip lasts exactly as long as its narration plus a breath on each side.  # Step: time the clip.
        durations.append(duration_of(seg_audio) + 2 * PAD)  # Clip duration in seconds.
        # Record the spoken line for the script file.  # Step: log the line.
        script_lines.append(f"[{idx:02d}] ({shot}) {text}")  # Shot name plus its exact narration.
    # Save the narration script next to the video for the submission record.  # Step: write the script.
    with open(os.path.join(HERE, "narration.txt"), "w", encoding="utf-8") as handle:  # Open narration.txt for writing.
        # Write one line per segment.  # Step: write lines.
        handle.write("\n".join(script_lines) + "\n")  # The exact words the film speaks.
    # Second pass: render one silent video clip and one padded audio piece per segment.  # Step: render pass.
    for idx, (shot, text) in enumerate(SEGMENTS, start=1):  # Same order as the narration pass.
        # Read this segment's clip duration back from the table.  # Step: fetch duration.
        dur = durations[idx - 1]  # Seconds this shot stays on screen.
        # Convert the duration to a whole frame count for the zoom filter.  # Step: frame count.
        frames = max(1, round(dur * FPS))  # zoompan works in frames, not seconds.
        # Measure the still so the right motion treatment is chosen.  # Step: measure still.
        still_w, still_h = size_of(os.path.join(SHOTS, shot))  # Native pixels of the capture.
        # Compute the still's height after scaling to the frame width.  # Step: scaled height.
        scaled_h = round(still_h * FRAME_W / still_w)  # What a full-width render would stand.
        # Tall stills (the routine cards) get a slow vertical pan from top to bottom; short stills get pad + gentle zoom.  # Branch: motion choice.
        if scaled_h > FRAME_H:  # The full card cannot fit the frame at readable size.
            # Build the pan filter: scale to frame width, then travel a 720-tall crop window downward across the clip.  # Step: compose pan filter.
            vf = (f"scale={FRAME_W}:-2,crop={FRAME_W}:{FRAME_H}:0:'(in_h-{FRAME_H})*t/{dur:.3f}',"
                  f"format=yuv420p,fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE}")  # Ends at the bottom of the card, where the totals and messages live.
        # Short stills are padded onto the page-colored frame and slowly zoomed, QuizForge style.  # Branch: pad + zoom.
        else:  # The whole still fits the frame with room to spare.
            # Alternate the slow zoom direction per shot so the slideshow feels alive.  # Step: pick the zoom.
            zoom = "min(zoom+0.0009,1.13)" if idx % 2 == 1 else "if(eq(on,0),1.13,max(zoom-0.0009,1.0))"  # Odd shots push in; even shots pull back.
            # Build the pad + zoom filter chain.  # Step: compose zoom filter.
            vf = (f"scale={FRAME_W}:-2,pad={FRAME_W}:{FRAME_H}:(ow-iw)/2:(oh-ih)/2:color={PAD_COLOR},scale=2560:1440,"
                  f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={FRAME_W}x{FRAME_H}:fps={FPS},"
                  f"format=yuv420p,fade=t=in:st=0:d={FADE},fade=t=out:st={dur - FADE:.3f}:d={FADE}")  # 720p output, gentle motion, clean fades.
        # Render this shot's silent clip.  # Step: render the clip.
        run(["ffmpeg", "-y", "-loop", "1", "-i", os.path.join(SHOTS, shot), "-vf", vf, "-t", f"{dur:.3f}",  # One still becomes one clip.
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-r", str(FPS), os.path.join(CLIPS, f"vid{idx:02d}.mp4")])  # H.264, web-standard settings.
        # Build this segment's audio piece: narration delayed by the head pad, then padded and trimmed to the clip length.  # Step: pad the audio.
        run(["ffmpeg", "-y", "-i", os.path.join(AUDIO, f"seg{idx:02d}.mp3"), "-af", f"adelay={int(PAD * 1000)}|{int(PAD * 1000)},apad,atrim=0:{dur:.3f}",  # Silence, voice, silence - exactly one clip long.
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", os.path.join(CLIPS, f"aud{idx:02d}.m4a")])  # AAC at a fixed sample rate so concat is clean.
    # Write the concat lists for the video clips and the audio pieces.  # Step: prepare concat.
    with open(os.path.join(CLIPS, "list_v.txt"), "w", encoding="utf-8") as handle:  # Open the video list.
        # Write one line per video clip, in order.  # Step: write video list.
        handle.write("".join(f"file 'vid{idx:02d}.mp4'\n" for idx in range(1, len(SEGMENTS) + 1)))  # The picture order.
    # Write the audio list the same way.  # Step: write audio list.
    with open(os.path.join(CLIPS, "list_a.txt"), "w", encoding="utf-8") as handle:  # Open the audio list.
        # Write one line per audio piece, in order.  # Step: write lines.
        handle.write("".join(f"file 'aud{idx:02d}.m4a'\n" for idx in range(1, len(SEGMENTS) + 1)))  # The voice order.
    # Concatenate the video clips into one silent track (identical codecs, so stream copy is safe).  # Step: join video.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(CLIPS, "list_v.txt"), "-c", "copy", os.path.join(CLIPS, "video_only.mp4")])  # The full picture track.
    # Concatenate the audio pieces into one narration track (re-encoded once for safety).  # Step: join audio.
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(CLIPS, "list_a.txt"), "-c:a", "aac", "-b:a", "160k", os.path.join(CLIPS, "audio_full.m4a")])  # The full voice track.
    # Mux picture and voice into the deliverable, with faststart so web players can stream it.  # Step: mux.
    final = os.path.join(HERE, "skinsense-demo.mp4")  # The finished demo video.
    # Combine the two tracks without re-encoding.  # Step: combine tracks.
    run(["ffmpeg", "-y", "-i", os.path.join(CLIPS, "video_only.mp4"), "-i", os.path.join(CLIPS, "audio_full.m4a"), "-c", "copy", "-movflags", "+faststart", final])  # Both tracks are already final-spec.
    # Probe the finished file and report its key facts.  # Step: verify.
    done = run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", final])  # Streams plus format.
    # Parse the probe output for the summary print.  # Step: summarize.
    info = json.loads(done.stdout)  # Dict of streams and format data.
    # Print the deliverable path and total duration.  # Step: report.
    print("FINAL:", final, "| duration:", info["format"]["duration"], "s | segments:", len(SEGMENTS), "| total narrated:", f"{sum(durations):.1f}", "s")  # One-line build summary.
# Run main() only when this file is executed directly.  # Entry-point guard.
if __name__ == "__main__":  # Check how the file was started.
    # Start the build.  # Step: entry.
    main()  # Narrate, render, concat, mux.
