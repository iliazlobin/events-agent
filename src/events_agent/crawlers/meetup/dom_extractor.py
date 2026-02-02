"""DOM extraction utilities for Meetup events."""

from typing import List, Dict
from playwright.sync_api import Page


class DOMExtractor:
    """Extracts event data from Meetup page DOM."""

    @staticmethod
    def extract_events(page: Page) -> List[Dict]:
        """
        Extract event data from DOM.

        Returns:
            List of dictionaries with event data
        """
        return page.evaluate('''() => {
            const events = [];
            const seen = new Set();

            // Find all time elements with datetime attributes
            const timeElements = document.querySelectorAll('time[datetime]');

            timeElements.forEach(timeEl => {
                const datetime = timeEl.getAttribute('datetime');
                if (!datetime) return;

                // Find parent event link
                let parent = timeEl;
                let link = null;
                for (let i = 0; i < 10; i++) {
                    parent = parent.parentElement;
                    if (!parent) break;

                    link = parent.querySelector('a[href*="/events/"]');
                    if (link) break;
                }

                if (!link) return;

                const href = link.getAttribute('href');
                const match = href.match(/\\/events\\/(\\d+)/);
                if (!match || seen.has(match[1])) return;

                seen.add(match[1]);

                // Find event container
                let container = link;
                for (let i = 0; i < 8; i++) {
                    container = container.parentElement;
                    if (!container) break;
                    if (container.textContent && container.textContent.length > 100) break;
                }

                if (!container) container = link.parentElement;

                // Extract title
                let title = '';
                const headings = container.querySelectorAll('h1, h2, h3, h4, [role="heading"]');
                if (headings.length > 0) {
                    title = headings[0].textContent?.trim() || '';
                } else {
                    const titleLink = container.querySelector('a[href*="/events/"] span, a[href*="/events/"]');
                    if (titleLink) {
                        title = titleLink.textContent?.trim() || '';
                    }
                }

                // Extract location
                const fullText = container.textContent || '';
                let location = '';
                const locationMatch = fullText.match(/(Brooklyn|Manhattan|Queens|Bronx|Staten Island|New York|NYC)/i);
                if (locationMatch) {
                    location = locationMatch[0];
                }

                events.push({
                    event_id: match[1],
                    title: title || 'Event',
                    url: href.startsWith('http') ? href : 'https://www.meetup.com' + href,
                    date_text: datetime,
                    location: location || 'New York',
                    attendees: 0
                });
            });

            // Also find event links without time elements
            const eventLinks = document.querySelectorAll('a[href*="/events/"]');

            eventLinks.forEach(link => {
                const href = link.getAttribute('href');
                const match = href.match(/\\/events\\/(\\d+)/);

                if (match) {
                    const eventId = match[1];

                    // Skip duplicates
                    if (seen.has(eventId)) return;
                    seen.add(eventId);

                    // Get event container (parent element)
                    const container = link.closest('article, [data-testid*="event"], section, div[id*="event"]');

                    // Extract title (from link text or heading)
                    let title = '';
                    const titleEl = container?.querySelector('h2, h3, [class*="title"]');
                    if (titleEl) {
                        title = titleEl.textContent?.trim() || '';
                    } else {
                        title = link.textContent?.trim() || '';
                    }

                    // Extract date/time text
                    let dateText = '';
                    const dateEl = container?.querySelector('time, [datetime], [class*="date"], [class*="time"]');
                    if (dateEl) {
                        dateText = dateEl.getAttribute('datetime') ||
                                  dateEl.textContent?.trim() || '';
                    }

                    // Extract location
                    let location = '';
                    const locationEl = container?.querySelector('[class*="location"], [class*="venue"]');
                    if (locationEl) {
                        location = locationEl.textContent?.trim() || '';
                    }

                    // Extract attendee count
                    let attendees = 0;
                    const attendeeText = container?.textContent || '';
                    const attendeeMatch = attendeeText.match(/(\\d+)\\s+attendees?/i);
                    if (attendeeMatch) {
                        attendees = parseInt(attendeeMatch[1]);
                    }

                    events.push({
                        event_id: eventId,
                        title: title,
                        url: href.startsWith('http') ? href : 'https://www.meetup.com' + href,
                        date_text: dateText,
                        location: location,
                        attendees: attendees
                    });
                }
            });

            return events;
        }''')
