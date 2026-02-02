"""Analyze a single event page to identify all extractable fields."""

import sys
sys.path.insert(0, 'src')

from playwright.sync_api import sync_playwright
import json

def analyze_event_page():
    """Analyze event detail page structure."""

    # Sample event URL
    event_url = "https://www.meetup.com/psychedelic-yoga/events/312850971/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading event page: {event_url}\n")
        page.goto(event_url, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(3000)

        # Extract all available data
        event_data = page.evaluate('''() => {
            const data = {
                basic: {},
                organizer: {},
                group: {},
                location: {},
                attendance: {},
                content: {},
                metadata: {}
            };

            // Basic info
            data.basic.title = document.querySelector('h1')?.textContent?.trim();

            // Description
            const descEl = document.querySelector('[class*="description"], [class*="eventDescription"]');
            data.content.description = descEl?.textContent?.trim() || '';
            data.content.description_html = descEl?.innerHTML || '';

            // AI Summary
            const summaryEl = document.querySelector('[class*="aiSummary"], [aria-label*="summary"]');
            data.content.ai_summary = summaryEl?.textContent?.trim();

            // Host/Organizer
            const hostEl = document.querySelector('[class*="host"], [class*="organizer"]');
            if (hostEl) {
                data.organizer.name = hostEl.textContent?.match(/Hosted by (.+)/)?.[1]?.trim();
            }

            // Speaker bio
            const speakerEl = document.querySelector('[class*="speaker"], [class*="bio"]');
            data.organizer.bio = speakerEl?.textContent?.trim();

            // Group info
            const groupLink = document.querySelector('a[href*="/"][class*="group"]');
            if (groupLink) {
                data.group.name = groupLink.textContent?.trim();
                data.group.url = groupLink.getAttribute('href');
            }

            // Rating
            const ratingEl = document.querySelector('[class*="rating"]');
            if (ratingEl) {
                const ratingText = ratingEl.textContent;
                data.group.rating = parseFloat(ratingText.match(/[\d.]+/)?.[0]);
                data.group.review_count = parseInt(ratingText.match(/(\\d+)\\s+reviews?/i)?.[1]);
            }

            // Location details
            const locationHeader = document.querySelector('h2, h3, [class*="venue"]');
            data.location.venue_name = locationHeader?.textContent?.trim();

            const addressEl = document.querySelector('[class*="address"]');
            data.location.full_address = addressEl?.textContent?.trim();

            // Attendees
            const attendeeEl = document.querySelector('[class*="attendee"], [class*="going"]');
            if (attendeeEl) {
                const attendeeText = attendeeEl.textContent;
                data.attendance.attendee_count = parseInt(attendeeText.match(/\\d+/)?.[0]);
            }

            // Price
            const priceEl = document.querySelector('[class*="price"], [class*="cost"]');
            if (priceEl) {
                const priceText = priceEl.textContent;
                data.attendance.price_text = priceText.trim();
                const priceMatch = priceText.match(/\\$([\\d.]+)/);
                if (priceMatch) {
                    data.attendance.price = parseFloat(priceMatch[1]);
                }
            }

            // Registration URL
            const regLinks = Array.from(document.querySelectorAll('a[href*="http"]'));
            const regLink = regLinks.find(l =>
                l.textContent?.match(/register|sign up|rsvp/i) ||
                l.href?.includes('register') ||
                l.href?.includes('studiogrowth')
            );
            data.metadata.registration_url = regLink?.href;

            // Images
            const images = Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                alt: img.alt
            })).filter(img => img.src && !img.src.includes('icon') && !img.src.includes('logo'));
            data.metadata.images = images.slice(0, 5);

            // All text content for debugging
            data.metadata.page_text = document.body.textContent?.substring(0, 1000);

            return data;
        }''');

        print("Extracted Data:\n")
        print(json.dumps(event_data, indent=2))

        # Save for analysis
        with open("event_page_analysis.json", "w") as f:
            json.dump(event_data, f, indent=2)

        print("\n✓ Saved to event_page_analysis.json")

        browser.close()

if __name__ == "__main__":
    analyze_event_page()
