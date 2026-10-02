import webbrowser
from livekit.api import AccessToken, VideoGrants
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("LIVEKIT_API_KEY")
api_secret = os.getenv("LIVEKIT_API_SECRET")
livekit_url = os.getenv("LIVEKIT_URL")

token = AccessToken(api_key, api_secret)
token.with_identity("student-tester").with_name("Student").with_grants(
    VideoGrants(room_join=True, room="priya-admissions-room")
)
jwt_token = token.to_jwt()

playground_url = f"https://agents-playground.livekit.io/#url={livekit_url}&token={jwt_token}"

print("=" * 70)
print("PRIYA MICROPHONE TEST - LIVEKIT PLAYGROUND")
print("=" * 70)
print("\nOpening your browser now to talk with Priya via microphone...")
print(f"\nIf it doesn't open automatically, open this link:\n\n{playground_url}\n")
print("=" * 70)

webbrowser.open(playground_url)
