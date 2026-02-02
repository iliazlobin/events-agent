"""Scraper for individual event detail pages."""

from typing import Dict, Any, Optional
from playwright.sync_api import Page
import time


class EventDetailScraper:
    """Scrapes additional details from individual event pages."""

    def __init__(self, rate_limit_seconds: float = 1.0):
        """
        Initialize detail scraper.

        Args:
            rate_limit_seconds: Delay between requests
        """
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time = 0

    def scrape_event_details(self, page: Page, event_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information from an event page.

        Args:
            page: Playwright Page object
            event_url: URL of the event detail page

        Returns:
            Dictionary with additional event details, or None if failed
        """
        # Rate limiting
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit_seconds:
            time.sleep(self.rate_limit_seconds - elapsed)

        try:
            # Load event page
            page.goto(event_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)
            self._last_request_time = time.time()

            # Extract data from Apollo state
            event_data = page.evaluate('''() => {
                const scriptTag = document.getElementById('__NEXT_DATA__');
                if (!scriptTag) return null;

                const data = JSON.parse(scriptTag.textContent);
                const apollo = data?.props?.pageProps?.__APOLLO_STATE__;
                if (!apollo) return null;

                // Find the Event: key
                const eventKey = Object.keys(apollo).find(k => k.startsWith('Event:'));
                if (!eventKey) return null;

                const event = apollo[eventKey];

                // Helper to resolve references
                function resolve(ref) {
                    if (ref && typeof ref === 'object' && ref.__ref) {
                        return apollo[ref.__ref] || {};
                    }
                    return ref || {};
                }

                // Extract all useful fields
                const details = {
                    // Basic
                    description: event.description,
                    ai_summary: event.aeoDescription,
                    end_datetime: event.endTime,

                    // Host
                    host_name: null,
                    host_bio: null,

                    // Group
                    group_name: null,
                    group_rating: null,
                    group_review_count: null,

                    // Venue details
                    venue_name: null,
                    full_address: null,
                    latitude: null,
                    longitude: null,
                    directions: null,

                    // Attendance
                    attendee_count: null,
                    waitlist_count: null,

                    // Pricing
                    fee_amount: null,
                    fee_required: null,
                    payment_methods: null,

                    // Media
                    image_url: null,
                    topics: [],

                    // External links
                    registration_url: null
                };

                // Extract speaker/host details
                if (event.speakerDetails) {
                    details.host_name = event.speakerDetails.name;
                    details.host_bio = event.speakerDetails.description;
                }

                // Extract from eventHosts array
                if (event.eventHosts && event.eventHosts.length > 0) {
                    const host = resolve(event.eventHosts[0]);
                    if (host.member) {
                        const member = resolve(host.member);
                        if (!details.host_name && member.name) {
                            details.host_name = member.name;
                        }
                    }
                }

                // Extract group details
                if (event.group) {
                    const group = resolve(event.group);
                    details.group_name = group.name;
                    details.group_rating = group.overallRating?.averageRating;
                    details.group_review_count = group.overallRating?.totalReviews;
                }

                // Extract venue details
                if (event.venue) {
                    const venue = resolve(event.venue);
                    details.venue_name = venue.name;
                    details.full_address = venue.address;
                    details.latitude = venue.lat;
                    details.longitude = venue.lon;

                    // Look for "how to find us" in description
                    if (event.description) {
                        const directionsMatch = event.description.match(/How to find us[:\\s]+([^\\n]{10,200})/i);
                        if (directionsMatch) {
                            details.directions = directionsMatch[1].trim();
                        }
                    }
                }

                // Extract attendance
                const yesRsvps = event['rsvps({"filter":{"rsvpStatus":["YES"]}})'];
                if (yesRsvps) {
                    details.attendee_count = yesRsvps.totalCount;
                }

                const waitlistRsvps = event['rsvps({"filter":{"rsvpStatus":["WAITLIST"]}})'];
                if (waitlistRsvps) {
                    details.waitlist_count = waitlistRsvps.totalCount;
                }

                // Extract pricing
                if (event.feeSettings) {
                    details.fee_amount = event.feeSettings.amount;
                    details.fee_required = event.feeSettings.required;
                    details.payment_methods = event.feeSettings.accepts;
                }

                // Extract image
                if (event.featuredEventPhoto) {
                    const photo = resolve(event.featuredEventPhoto);
                    if (photo.baseUrl) {
                        details.image_url = photo.baseUrl;
                    }
                }

                // Extract topics
                if (event.topics && event.topics.edges) {
                    details.topics = event.topics.edges.map(edge => {
                        const topic = resolve(edge.node);
                        return topic.name;
                    }).filter(Boolean);
                }

                // Look for registration URL in description
                if (event.description) {
                    const urlMatch = event.description.match(/https?:\\/\\/[^\\s<>\"]+/g);
                    if (urlMatch) {
                        // Filter for registration-like URLs
                        const regUrl = urlMatch.find(url =>
                            url.includes('register') ||
                            url.includes('signup') ||
                            url.includes('rsvp') ||
                            url.includes('eventbrite') ||
                            url.includes('studiogrowth') ||
                            url.includes('tock.com')
                        );
                        if (regUrl) {
                            details.registration_url = regUrl;
                        }
                    }
                }

                return details;
            }''')

            if event_data:
                return event_data
            else:
                print(f"      No Apollo state found for {event_url}")
                return None

        except Exception as e:
            print(f"      Error scraping {event_url}: {e}")
            return None

    def enhance_event(self, event_dict: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge detail page data into event dictionary.

        Args:
            event_dict: Base event data
            details: Additional details from detail page

        Returns:
            Enhanced event dictionary
        """
        # Add all detail fields
        enhanced = event_dict.copy()

        # Update with detail page data (only if not already present)
        for key, value in details.items():
            if value is not None:
                # Map some field names
                if key == 'venue_name':
                    enhanced['location_name'] = value
                elif key == 'full_address':
                    enhanced['location_address'] = value
                else:
                    enhanced[key] = value

        # Mark as detail-crawled
        enhanced['detail_crawled'] = True

        return enhanced
