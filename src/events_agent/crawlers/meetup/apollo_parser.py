"""Apollo GraphQL state parsing for Meetup."""

from typing import Dict, Any, Optional
from playwright.sync_api import Page


class ApolloParser:
    """Parses Apollo GraphQL state from Meetup pages."""

    @staticmethod
    def extract_apollo_state(page: Page) -> Dict[str, Any]:
        """
        Extract Apollo state from __NEXT_DATA__ script tag.

        Args:
            page: Playwright Page object

        Returns:
            Apollo state dictionary (empty dict if not found)
        """
        next_data = page.evaluate('''() => {
            const scriptTag = document.getElementById('__NEXT_DATA__');
            if (scriptTag) {
                return JSON.parse(scriptTag.textContent);
            }
            return null;
        }''')

        if not next_data:
            return {}

        return next_data.get('props', {}).get('pageProps', {}).get('__APOLLO_STATE__', {})

    @staticmethod
    def get_event_count(apollo_state: Dict[str, Any]) -> int:
        """
        Count events in Apollo state.

        Args:
            apollo_state: Apollo state dictionary

        Returns:
            Number of Event: keys found
        """
        return len([k for k in apollo_state.keys() if k.startswith('Event:')]) if apollo_state else 0

    @staticmethod
    def get_event_data(apollo_state: Dict[str, Any], event_id: str) -> Optional[Dict[str, Any]]:
        """
        Get event data from Apollo state by ID.

        Args:
            apollo_state: Apollo state dictionary
            event_id: Event ID to look up

        Returns:
            Event data dictionary or None if not found
        """
        apollo_key = f"Event:{event_id}"
        return apollo_state.get(apollo_key)

    @staticmethod
    def resolve_reference(ref_obj: Any, apollo_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve Apollo GraphQL references.

        Args:
            ref_obj: Reference object (may contain __ref key)
            apollo_state: Full Apollo state for lookup

        Returns:
            Resolved object or empty dict
        """
        if isinstance(ref_obj, dict) and '__ref' in ref_obj:
            return apollo_state.get(ref_obj['__ref'], {})
        return ref_obj or {}
