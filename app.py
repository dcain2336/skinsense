# app.py - the SkinSense Agent web server.  # Module header: what this file is.
# SkinSense Agent is an agentic skincare prototype for the YouCam API Skin AI & eCommerce VTO Hackathon (Perfect Corp, Devpost, deadline Nov 2, 2026).  # Context: which contest this serves.
# Routes: GET / (the single-page UI), GET /api/status (mode + integration health), POST /api/analyze (concern + optional photo -> analysis + routine), POST /api/refine (feedback + state -> updated routine), POST /api/tryon (virtual try-on intent for one product).  # Routes: the whole API surface.
# Still zero-dependency: Python standard library only, no pip installs needed, so it runs anywhere Python 3 runs.  # Design choice: stdlib only, like QuizForge.
# The YouCam API key stays server-side: the browser only ever talks to these routes, never to Perfect Corp directly.  # Security: key never reaches the client.
# Import the base64 module so uploaded photo data URLs can be decoded into bytes.  # Library: base64.
import base64  # Data URL decoding for the photo upload.
# Import the JSON module so the API can speak JSON.  # Library: json.
import json  # Make the json module available.
# Import the OS module so the server can read the PORT environment variable.  # Library: os.
import os  # Make the os module available.
# Import BaseHTTPRequestHandler and ThreadingHTTPServer from the standard http.server module.  # Library: http.server.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # The request-handler base class and a threaded server.
# Import the sibling agent module that runs the analyze -> recommend -> refine loop.  # Library: agent (this project).
import agent  # The agentic loop lives in agent.py.
# Import the sibling YouCam client so the status route can report configuration honestly.  # Library: youcam (this project).
import youcam  # The documented REST client lives in youcam.py.
# Import the sibling catalog so the try-on route can validate product identifiers.  # Library: catalog (this project).
import catalog  # The demo product list lives in catalog.py.
# Define the directory this file lives in, so static files resolve from anywhere.  # Constant: project root.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the project folder.
# Define the path of the single-page UI file.  # Constant: UI file path.
INDEX_PATH = os.path.join(BASE_DIR, "static", "index.html")  # The front-end page served at GET /.
# Define the default port; the PORT environment variable can override it.  # Constant: listen port.
PORT = int(os.environ.get("PORT", "8770"))  # 8770 avoids clashing with QuizForge Live on 8765.
# Define the largest photo the server will accept, matching the API's documented 10 MB ceiling.  # Constant: photo size cap.
MAX_PHOTO_BYTES = 10 * 1024 * 1024  # The docs cap skin-analysis inputs at 10 MB.
# Start the helper that parses a JSON POST body and returns the payload dictionary.  # Function: read_json_body.
def read_json_body(handler):  # Define read_json_body, which reads and parses the request body.
    # Read the declared request-body length, defaulting to zero.  # Step: body length.
    length = int(handler.headers.get("Content-Length", "0"))  # The client tells us how many bytes to read.
    # Read exactly that many bytes from the request body.  # Step: read the body.
    raw_body = handler.rfile.read(length)  # The raw JSON the browser sent.
    # Parse the body as JSON.  # Step: parse the body.
    return json.loads(raw_body.decode("utf-8"))  # Convert bytes into a dictionary.
# Start the helper that converts a browser photo data URL into the photo dict the agent expects.  # Function: decode_photo.
def decode_photo(data_url):  # Define decode_photo with the data URL string (or None/empty).
    # Treat a missing or empty value as "no photo provided".  # Branch: no photo.
    if not data_url:  # The text-only path is a first-class flow, not an error.
        # Return None so the agent takes the text-guided path.  # Step: return none.
        return None  # The agent labels that path SAMPLE, honestly.
    # Split the data URL into its header and its base64 payload.  # Step: split data URL.
    header, separator, payload = data_url.partition(",")  # Shape: "data:image/jpeg;base64,....".
    # Validate the split actually found the separator.  # Branch: malformed.
    if not separator:  # A plain string without a comma is not a data URL.
        # Raise a readable error the API turns into a 400.  # Step: raise malformed.
        raise ValueError("Photo data was not a valid data URL")  # Honest client error.
    # Extract the MIME type from the header, defaulting to JPEG.  # Step: mime type.
    content_type = header.split(";")[0].replace("data:", "") or "image/jpeg"  # Browsers send image/jpeg or image/png here.
    # Decode the base64 payload into raw image bytes.  # Step: decode bytes.
    image_bytes = base64.b64decode(payload)  # The exact bytes the File API will register.
    # Enforce the documented 10 MB input ceiling before anything is uploaded.  # Branch: too large.
    if len(image_bytes) > MAX_PHOTO_BYTES:  # Oversized photos would be rejected by the API anyway.
        # Raise a readable size error.  # Step: raise size error.
        raise ValueError("Photo is larger than the 10 MB API limit")  # Fail fast, before any network call.
    # Build the photo dictionary in the shape the agent and client share.  # Step: build photo dict.
    photo = {  # Open the photo dictionary.
        "bytes": image_bytes,  # The raw image bytes.
        "content_type": content_type,  # The MIME type for the File API metadata.
        "file_name": "skinsense-selfie." + ("png" if content_type == "image/png" else "jpg"),  # A stable, honest file name.
    }  # Close the photo dictionary.
    # Return the decoded photo.  # Step: return photo.
    return photo  # The agent passes this straight to the YouCam client in live mode.
# Start the request-handler class that answers every HTTP request.  # Class: SkinSenseHandler.
class SkinSenseHandler(BaseHTTPRequestHandler):  # Define the handler by extending the standard base class.
    # Silence the default per-request stderr logging so demo output stays readable.  # Method: log_message (muted).
    def log_message(self, format, *args):  # Override the base logging hook.
        pass  # Do nothing: keep the console clean.
    # Start the helper that sends a JSON response with a chosen status code.  # Method: send_json.
    def send_json(self, status, payload):  # Define send_json, which serializes a dictionary to the client.
        # Serialize the payload to UTF-8 JSON bytes.  # Step: encode the body.
        body = json.dumps(payload).encode("utf-8")  # Convert the dictionary into bytes.
        # Send the HTTP status line.  # Step: status line.
        self.send_response(status)  # Write the status code.
        # Declare the JSON content type.  # Step: content-type header.
        self.send_header("Content-Type", "application/json; charset=utf-8")  # Tell the client the body is JSON.
        # Declare the exact body length so the client knows when it ends.  # Step: length header.
        self.send_header("Content-Length", str(len(body)))  # Byte length of the body.
        # Finish the header block.  # Step: end headers.
        self.end_headers()  # Blank line that ends the headers.
        # Write the body bytes to the client.  # Step: write the body.
        self.wfile.write(body)  # Send the JSON payload.
    # Start the helper that sends a plain file with a chosen content type.  # Method: send_file.
    def send_file(self, path, content_type):  # Define send_file, which streams a file from disk.
        # Read the whole file as bytes.  # Step: read the file.
        with open(path, "rb") as handle:  # Open in binary mode and auto-close afterwards.
            body = handle.read()  # Load the file contents.
        # Send a 200 OK status line.  # Step: status line.
        self.send_response(200)  # The file exists and is being served.
        # Declare the caller-provided content type.  # Step: content-type header.
        self.send_header("Content-Type", content_type)  # HTML for the single page.
        # Declare the exact body length.  # Step: length header.
        self.send_header("Content-Length", str(len(body)))  # Byte length of the file.
        # Finish the header block.  # Step: end headers.
        self.end_headers()  # Blank line that ends the headers.
        # Write the file bytes to the client.  # Step: write the body.
        self.wfile.write(body)  # Send the file contents.
    # Start the GET router: the home page and the status snapshot.  # Method: do_GET.
    def do_GET(self):  # Define do_GET, which the server calls for every GET request.
        # Route the root path to the single-page UI.  # Branch: home page.
        if self.path == "/":  # Check for the root path.
            self.send_file(INDEX_PATH, "text/html; charset=utf-8")  # Serve the front-end page.
        # Route /api/status to the integration health snapshot.  # Branch: status.
        elif self.path == "/api/status":  # The UI polls this once on load for its mode badge.
            # Report the mode facts honestly: key presence (never the key), base URL, and flow shape.  # Step: status payload.
            self.send_json(200, {  # Open the status payload.
                "youcam_configured": youcam.is_configured(),  # True only when YOUCAM_API_KEY is set.
                "mode": "live-ready" if youcam.is_configured() else "sample",  # Live still needs a photo per request; the label says "ready", not "live".
                "api_base": youcam.BASE_URL,  # The documented host (or its env override).
                "api_version": youcam.API_VERSION,  # The task-path version in use.
                "dst_actions": youcam.DST_ACTIONS,  # The SD concerns each live analysis requests.
            })  # Close the status payload.
        # Answer every other GET path with a plain 404 JSON error.  # Branch: unknown path.
        else:  # No other GET routes exist in this prototype.
            self.send_json(404, {"error": "Unknown path: " + self.path})  # Honest 404 instead of a silent hang.
    # Start the POST router: analyze, refine, and try-on intent.  # Method: do_POST.
    def do_POST(self):  # Define do_POST, which the server calls for every POST request.
        # Guard the whole router so bad input becomes a JSON 400, never a dropped connection.  # Step: guarded router.
        try:  # Begin the guarded routing block.
            # Route /api/analyze to the first step of the agentic loop.  # Branch: analyze.
            if self.path == "/api/analyze":  # The browser sends concern text plus an optional photo data URL.
                # Parse the request JSON.  # Step: parse body.
                payload = read_json_body(self)  # Fields: concern, photo_data_url.
                # Decode the optional photo into the agent's photo shape.  # Step: decode photo.
                photo = decode_photo(payload.get("photo_data_url"))  # Raises ValueError on malformed or oversize input.
                # Run the loop: live when possible, labeled SAMPLE otherwise.  # Step: run analysis.
                result = agent.run_analysis(payload.get("concern", ""), photo)  # The agent owns the honesty labels.
                # Return the full result, including the session state for refine rounds.  # Step: send result.
                self.send_json(200, result)  # The client stores result.state verbatim.
            # Route /api/refine to the feedback step of the loop.  # Branch: refine.
            elif self.path == "/api/refine":  # The browser sends feedback text plus the stored state.
                # Parse the request JSON.  # Step: parse body.
                payload = read_json_body(self)  # Fields: feedback, state.
                # Run the refine step against the stored state.  # Step: run refine.
                result = agent.refine(payload.get("feedback", ""), payload.get("state", {}))  # Constraints accumulate across rounds.
                # Return the updated routine, the change notes, and the new state.  # Step: send result.
                self.send_json(200, result)  # The client replaces its stored state with result.state.
            # Route /api/tryon to the virtual try-on intent for one product card.  # Branch: try-on.
            elif self.path == "/api/tryon":  # The browser sends a product_id from a tint card.
                # Parse the request JSON.  # Step: parse body.
                payload = read_json_body(self)  # Fields: product_id.
                # Look the product up so unknown identifiers fail honestly.  # Step: look up product.
                product = catalog.by_id(payload.get("product_id", ""))  # None when the id is bogus.
                # Reject unknown products with a 404.  # Branch: unknown product.
                if product is None:  # The card should never send this, but honesty beats a crash.
                    # Send the 404 error.  # Step: send 404.
                    self.send_json(404, {"error": "Unknown product_id"})  # Plain, readable failure.
                # Reject products that have no try-on effect.  # Branch: no VTO.
                elif not product.get("vto"):  # Only tint products carry a makeup effect.
                    # Send a 400 explaining the product has no try-on.  # Step: send 400.
                    self.send_json(400, {"error": "This product has no virtual try-on"})  # The UI only shows the button on VTO cards anyway.
                # Answer honestly about the try-on state in this skeleton.  # Branch: VTO product.
                else:  # A real tint product was requested.
                    # Report that live try-on needs the key plus the user's photo task, and is wired as the next integration step.  # Step: send try-on status.
                    self.send_json(200, {  # Open the try-on payload.
                        "status": "not-yet-live",  # TODO(live key): start a YouCam Makeup VTO task (POST /s2s/v2.0/task/makeup-vto) with the user's uploaded photo file_id and this product's vto_effect, then poll it like skin-analysis.
                        "product_id": product["id"],  # Echo the product so the UI can label its message.
                        "effect": product.get("vto_effect", ""),  # The YouCam makeup effect this card maps to.
                        "message": "Virtual try-on for " + product["name"] + " runs through YouCam Makeup VTO. In this build it is a labeled placeholder: the VTO API requires the photo at a publicly accessible URL, and SkinSense never publishes a user's face photo, so the try-on task is not started from this build.",  # Plain-language honesty for the demo.
                    })  # Close the try-on payload.
            # Answer every other POST path with a plain 404 JSON error.  # Branch: unknown path.
            else:  # No other POST routes exist in this prototype.
                self.send_json(404, {"error": "Unknown path: " + self.path})  # Honest 404.
        # Turn malformed JSON, bad photos, and other value errors into a JSON 400.  # Handler: bad input.
        except (ValueError, json.JSONDecodeError) as error:  # Both failure kinds mean the client sent something unusable.
            # Send the 400 with the error's own message.  # Step: send 400.
            self.send_json(400, {"error": str(error)})  # The browser shows this text to the user.
# Start the entry point that runs when this file is executed directly.  # Block: main guard.
if __name__ == "__main__":  # Only start the server when run as a script, not when imported.
    # Create the threaded HTTP server bound to all interfaces on the chosen port.  # Step: create server.
    server = ThreadingHTTPServer(("", PORT), SkinSenseHandler)  # Threaded so a slow live poll never blocks the UI.
    # Announce the address so the demo operator knows where to point the browser.  # Step: announce.
    print("SkinSense Agent listening on http://localhost:" + str(PORT) + " (YouCam key configured: " + str(youcam.is_configured()) + ")")  # Mode honesty starts at the console.
    # Serve requests until the process is stopped.  # Step: serve forever.
    server.serve_forever()  # Ctrl+C ends the demo.
