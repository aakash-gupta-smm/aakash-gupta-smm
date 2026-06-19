import os
import webbrowser
import urllib.parse
import urllib.request
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

CLIENT_ID = "86snpk1ih44pxu"
CLIENT_SECRET = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "openid profile email w_member_social"

auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("Done! Go back to Terminal.".encode("ascii"))
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write("Error.".encode("ascii"))

    def log_message(self, format, *args):
        pass

def main():
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "aakash_agent"
    })
    auth_url = "https://www.linkedin.com/oauth/v2/authorization?" + params

    print("Opening LinkedIn in your browser...")
    print("Log in and click Allow.\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("No code received. Try again.")
        return

    print("Got code. Fetching access token...")

    token_data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode("ascii")

    req = urllib.request.Request(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )

    with urllib.request.urlopen(req) as resp:
        token_resp = json.loads(resp.read())

    access_token = token_resp.get("access_token")

    urn_req = urllib.request.Request(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": "Bearer " + access_token}
    )
    with urllib.request.urlopen(urn_req) as resp:
        profile = json.loads(resp.read())

    person_id = profile.get("sub")
    person_urn = "urn:li:person:" + person_id

    print("\n========================================")
    print("SUCCESS - Save these two values:")
    print("========================================")
    print("\nLINKEDIN_ACCESS_TOKEN=" + access_token)
    print("\nLINKEDIN_PERSON_URN=" + person_urn)
    print("\n========================================\n")

if __name__ == "__main__":
    main()
