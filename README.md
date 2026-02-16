# BetaView 🧗

AI-powered climbing technique analysis. Upload a bouldering video, get feedback like having a coach in your pocket.

## Features

- **Path Efficiency Analysis** - Track hip movement to measure climbing efficiency
- **Foot Stability Detection** - Identify micro-adjustments and "silent feet" quality
- **Movement Rhythm Analysis** - Analyze tempo and pause patterns
- **Body Tension Monitoring** - Detect core engagement and torso control
- **AI Coach Feedback** - Natural language technique tips powered by Claude

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Next.js   │────▶│   FastAPI   │────▶│  MediaPipe  │
│  Frontend   │     │   Backend   │     │    Pose     │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Claude    │
                    │   Coach     │
                    └─────────────┘
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY=your_key_here

# Run server
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analyze` | Upload video for analysis |
| GET | `/job/{id}` | Get job status |
| GET | `/job/{id}/result` | Get analysis results |
| GET | `/video/{id}` | Download annotated video |
| DELETE | `/job/{id}` | Delete job and files |

## Metrics Explained

### Path Efficiency
Ratio of direct distance to total distance traveled by hips. Higher = more controlled movement.
- 0.7+ = Excellent
- 0.5-0.7 = Good
- <0.5 = Needs work

### Foot Stability
Measures micro-adjustments after foot placements. Lower jitter = "silent feet".

### Body Tension
Tracks shoulder-hip alignment. Higher score = better core engagement.

### Movement Rhythm
Analyzes consistency of move/pause patterns. Low variance = deliberate climbing.

## Deployment

### Backend (Railway/Fly.io)

```bash
# Using Railway
railway login
railway init
railway up
```

### Frontend (Vercel)

```bash
cd frontend
vercel
```

Set `NEXT_PUBLIC_API_URL` to your backend URL.

## Environment Variables

### Backend
- `ANTHROPIC_API_KEY` - For coach feedback generation
- `UPLOAD_DIR` - Video upload directory (default: /tmp/betaview/uploads)
- `OUTPUT_DIR` - Processed video directory (default: /tmp/betaview/outputs)

### Frontend
- `NEXT_PUBLIC_API_URL` - Backend API URL

## Tech Stack

- **Frontend**: Next.js 14, React, TailwindCSS
- **Backend**: FastAPI, MediaPipe, OpenCV
- **AI**: Claude (Anthropic) for coaching feedback
- **Video**: MediaPipe Pose for skeleton tracking

## License

MIT

## Contributing

PRs welcome! Please read CONTRIBUTING.md first.
