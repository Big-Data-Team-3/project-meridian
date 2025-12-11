#!/usr/bin/env python3
"""
Test script for SSE streaming API.
This script demonstrates how to connect to the SSE endpoint and receive real-time updates.
"""

import asyncio
import json
import httpx
import time
from typing import Dict, Any

async def test_sse_streaming():
    """Test the SSE streaming endpoint."""
    base_url = "http://localhost:8000"  # Adjust if your backend runs on different port

    # Test data
    payload = {
        "company_name": "AAPL",
        "trade_date": "2024-12-19",
        "conversation_context": [
            {
                "id": "msg-123",
                "role": "user",
                "content": "Should I buy Apple stock?",
                "timestamp": "2024-12-19T10:00:00Z"
            }
        ]
    }

    print("🚀 Starting SSE streaming test...")
    print(f"📡 Connecting to: {base_url}/api/streaming/analyze")
    print(f"📊 Test data: {json.dumps(payload, indent=2)}")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Note: httpx doesn't support SSE directly, so we'll use the regular POST
            # In a real frontend, you'd use EventSource API
            print("⚠️  Note: Using regular HTTP POST for testing.")
            print("💡 In browser, use: new EventSource('/api/streaming/analyze')")
            print()

            response = await client.post(
                f"{base_url}/api/streaming/analyze",
                json=payload,
                headers={"Accept": "text/event-stream"}
            )

            if response.status_code == 200:
                print("✅ SSE endpoint responded successfully!")
                print("📝 Raw SSE response:")
                print("-" * 40)

                # Parse SSE response line by line
                lines = response.text.split('\n')
                for line in lines:
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            print(f"📊 Event: {data.get('event_type', 'unknown')}")
                            print(f"   Message: {data.get('message', 'N/A')}")
                            if data.get('agent_name'):
                                print(f"   Agent: {data.get('agent_name')}")
                            if data.get('progress') is not None:
                                print(f"   Progress: {data.get('progress')}%")
                            print()
                        except json.JSONDecodeError:
                            print(f"📝 Raw line: {line}")

                print("=" * 60)
                print("✅ Test completed successfully!")

            else:
                print(f"❌ SSE endpoint returned error: {response.status_code}")
                print(f"Response: {response.text}")

    except httpx.ConnectError:
        print("❌ Could not connect to backend server.")
        print("💡 Make sure the backend is running: python -m meridian-backend.server")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


async def test_sse_health():
    """Test the streaming health endpoint."""
    base_url = "http://localhost:8000"

    print("\n🏥 Testing streaming health endpoint...")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/streaming/health")

            if response.status_code == 200:
                data = response.json()
                print("✅ Health check passed!")
                print(f"   Status: {data.get('status')}")
                print(f"   Service: {data.get('service')}")
                print(f"   Features: {', '.join(data.get('features', []))}")
            else:
                print(f"❌ Health check failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Health check error: {e}")


def create_html_test_page():
    """Create a simple HTML page to test SSE in browser."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSE Streaming Test</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .event { border: 1px solid #ccc; margin: 10px 0; padding: 10px; border-radius: 5px; }
        .start { background-color: #e8f5e8; }
        .progress { background-color: #e8f4fd; }
        .agent_update { background-color: #fff3cd; }
        .complete { background-color: #d4edda; }
        .error { background-color: #f8d7da; }
        #startBtn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        #startBtn:disabled { background: #ccc; }
    </style>
</head>
<body>
    <h1>🚀 SSE Agent Analysis Streaming Test</h1>

    <button id="startBtn">Start Agent Analysis</button>

    <div id="events"></div>

    <script>
        const startBtn = document.getElementById('startBtn');
        const eventsDiv = document.getElementById('events');

        startBtn.addEventListener('click', startAnalysis);

        function startAnalysis() {
            startBtn.disabled = true;
            startBtn.textContent = 'Analysis Running...';

            // Clear previous events
            eventsDiv.innerHTML = '';

            // Create EventSource for SSE
            const eventSource = new EventSource('/api/streaming/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company_name: 'AAPL',
                    trade_date: '2024-12-19'
                })
            });

            eventSource.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    displayEvent(data);
                } catch (e) {
                    console.error('Failed to parse event data:', event.data);
                }
            };

            eventSource.onerror = function(error) {
                console.error('SSE Error:', error);
                displayEvent({
                    event_type: 'error',
                    message: 'Connection error occurred',
                    timestamp: new Date().toISOString()
                });
                eventSource.close();
                resetButton();
            };

            // Close connection when analysis completes
            eventSource.addEventListener('complete', () => {
                eventSource.close();
                resetButton();
            });
        }

        function displayEvent(data) {
            const eventDiv = document.createElement('div');
            eventDiv.className = `event ${data.event_type}`;

            const timestamp = new Date(data.timestamp).toLocaleTimeString();

            eventDiv.innerHTML = `
                <strong>${data.event_type.toUpperCase()}</strong> - ${timestamp}<br>
                <strong>Message:</strong> ${data.message}<br>
                ${data.agent_name ? `<strong>Agent:</strong> ${data.agent_name}<br>` : ''}
                ${data.progress !== undefined ? `<strong>Progress:</strong> ${data.progress}%<br>` : ''}
                ${data.data ? `<strong>Data:</strong> <pre>${JSON.stringify(data.data, null, 2)}</pre>` : ''}
            `;

            eventsDiv.appendChild(eventDiv);
            eventsDiv.scrollTop = eventsDiv.scrollHeight;
        }

        function resetButton() {
            startBtn.disabled = false;
            startBtn.textContent = 'Start Agent Analysis';
        }
    </script>
</body>
</html>"""

    with open('sse_test.html', 'w') as f:
        f.write(html_content)

    print("📄 Created sse_test.html for browser testing")
    print("💡 Serve this file from your backend or open directly in browser")


if __name__ == "__main__":
    print("🧪 SSE Streaming API Test")
    print("=" * 60)

    # Run async tests
    asyncio.run(test_sse_health())
    asyncio.run(test_sse_streaming())

    # Create HTML test page
    create_html_test_page()

    print("\n📋 Next steps:")
    print("1. Start your backend: cd meridian-backend && python server.py")
    print("2. Run this test: python test_sse_streaming.py")
    print("3. Open sse_test.html in browser for interactive testing")
    print("4. Check browser Network tab to see SSE events")
