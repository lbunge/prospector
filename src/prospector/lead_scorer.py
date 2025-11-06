"""Lead scoring and prioritization engine."""

from typing import Dict, List
from datetime import datetime


class LeadScorer:
    """Score and prioritize leads based on multiple factors."""

    def __init__(self):
        """Initialize lead scorer."""
        pass

    def score_lead(self, business_data: Dict) -> Dict:
        """
        Calculate comprehensive lead score (0-100).

        Args:
            business_data: Complete business data

        Returns:
            Scoring breakdown and total score
        """
        scores = {
            'total': 0,
            'breakdown': {},
            'grade': 'F',
            'priority': 'low',
            'reasons': []
        }

        # Factor 1: Contact Information Quality (0-25 points)
        contact_score = self._score_contact_quality(business_data)
        scores['breakdown']['contact_quality'] = contact_score
        scores['total'] += contact_score

        # Factor 2: Business Legitimacy & Quality (0-20 points)
        legitimacy_score = self._score_legitimacy(business_data)
        scores['breakdown']['legitimacy'] = legitimacy_score
        scores['total'] += legitimacy_score

        # Factor 3: Local vs Corporate (0-15 points)
        local_score = self._score_local_preference(business_data)
        scores['breakdown']['local_preference'] = local_score
        scores['total'] += local_score

        # Factor 4: Online Presence & Engagement (0-15 points)
        presence_score = self._score_online_presence(business_data)
        scores['breakdown']['online_presence'] = presence_score
        scores['total'] += presence_score

        # Factor 5: Reputation & Reviews (0-15 points)
        reputation_score = self._score_reputation(business_data)
        scores['breakdown']['reputation'] = reputation_score
        scores['total'] += reputation_score

        # Factor 6: Business Size & Opportunity (0-10 points)
        opportunity_score = self._score_opportunity(business_data)
        scores['breakdown']['opportunity'] = opportunity_score
        scores['total'] += opportunity_score

        # Calculate grade
        scores['grade'] = self._calculate_grade(scores['total'])

        # Calculate priority
        scores['priority'] = self._calculate_priority(scores['total'])

        # Generate reasons for score
        scores['reasons'] = self._generate_score_reasons(business_data, scores['breakdown'])

        return scores

    def _score_contact_quality(self, data: Dict) -> float:
        """
        Score quality and availability of contact information.

        Max: 25 points
        """
        score = 0.0

        # Email availability (0-12 points)
        emails = data.get('emails_found', [])
        email_count = len(emails)

        if email_count >= 3:
            score += 12
        elif email_count == 2:
            score += 10
        elif email_count == 1:
            score += 7

        # Email validation (0-5 points)
        validated_emails = [
            e for e in emails
            if e.get('validation', {}).get('is_deliverable', False)
        ]
        if validated_emails:
            validation_rate = len(validated_emails) / email_count if email_count > 0 else 0
            score += validation_rate * 5

        # Person-specific emails (0-3 points)
        person_emails = [e for e in emails if e.get('type') == 'person']
        if person_emails:
            score += min(len(person_emails), 3)

        # Phone number availability (0-3 points)
        if data.get('phone'):
            score += 3
            # Validated phone (0-2 extra points)
            phone_validation = data.get('phone_validation', {})
            if phone_validation.get('valid'):
                score += 2

        return min(score, 25)

    def _score_legitimacy(self, data: Dict) -> float:
        """
        Score business legitimacy and quality signals.

        Max: 20 points
        """
        score = 0.0

        # Has website (0-5 points)
        if data.get('website'):
            score += 5

            # Website confidence (0-2 points)
            confidence = data.get('website_confidence', 'low')
            if confidence == 'high':
                score += 2
            elif confidence == 'medium':
                score += 1

        # Google Maps presence (0-3 points)
        if data.get('place_id'):
            score += 3

        # Business is open (0-5 points)
        business_status = data.get('business_status') or ''
        if business_status.lower() == 'operational':
            score += 5
        elif business_status.lower() == 'open':
            score += 5

        # Has verified phone (0-2 points)
        if data.get('formatted_phone_number') or data.get('phone'):
            score += 2

        # Yelp verification (0-3 points)
        if data.get('yelp_data'):
            score += 2
            if data['yelp_data'].get('is_claimed'):
                score += 1

        return min(score, 20)

    def _score_local_preference(self, data: Dict) -> float:
        """
        Score based on local vs corporate nature.

        Max: 15 points (prioritizes local businesses)
        """
        score = 0.0

        franchise_data = data.get('franchise_detection', {})

        # Is local/independent (0-10 points)
        if franchise_data.get('is_local', True):
            score += 10
        elif not franchise_data.get('is_franchise'):
            score += 5

        # Has local phone number (0-3 points)
        if data.get('phone') and not data.get('phone_validation', {}).get('is_toll_free'):
            score += 3

        # Has local email (0-2 points)
        local_hints = data.get('local_contact_hints', {})
        if local_hints.get('has_local_email'):
            score += 2

        return min(score, 15)

    def _score_online_presence(self, data: Dict) -> float:
        """
        Score online presence and digital engagement.

        Max: 15 points
        """
        score = 0.0

        # Has website (0-5 points)
        if data.get('website'):
            score += 5

        # Social media presence (0-5 points)
        social_media = data.get('social_media', {})
        social_count = len(social_media)
        score += min(social_count * 1.5, 5)

        # Yelp presence (0-2 points)
        if data.get('yelp_data'):
            score += 2

        # Google Maps photos (0-2 points)
        photos = data.get('photos', [])
        if len(photos) > 0:
            score += 2

        # Has Google Maps reviews (0-1 point)
        if data.get('user_ratings_total', 0) > 0:
            score += 1

        return min(score, 15)

    def _score_reputation(self, data: Dict) -> float:
        """
        Score based on reputation and reviews.

        Max: 15 points
        """
        score = 0.0

        # Google rating (0-7 points)
        rating = data.get('rating')
        if rating:
            # 4.5-5.0 = 7 points, 4.0-4.4 = 5 points, 3.5-3.9 = 3 points, <3.5 = 1 point
            if rating >= 4.5:
                score += 7
            elif rating >= 4.0:
                score += 5
            elif rating >= 3.5:
                score += 3
            elif rating >= 3.0:
                score += 1

        # Review count (0-5 points)
        review_count = data.get('user_ratings_total', 0)
        if review_count >= 100:
            score += 5
        elif review_count >= 50:
            score += 4
        elif review_count >= 20:
            score += 3
        elif review_count >= 10:
            score += 2
        elif review_count >= 5:
            score += 1

        # Yelp rating (0-3 points)
        yelp_data = data.get('yelp_data', {})
        yelp_rating = yelp_data.get('yelp_rating')
        if yelp_rating:
            if yelp_rating >= 4.0:
                score += 3
            elif yelp_rating >= 3.5:
                score += 2
            elif yelp_rating >= 3.0:
                score += 1

        return min(score, 15)

    def _score_opportunity(self, data: Dict) -> float:
        """
        Score business size and opportunity potential.

        Max: 10 points
        """
        score = 0.0

        # Popular business (0-4 points)
        if data.get('is_popular'):
            score += 4

        # Multiple locations might mean bigger opportunity (0-3 points)
        review_count = data.get('user_ratings_total', 0)
        if review_count >= 100:
            score += 3
        elif review_count >= 50:
            score += 2

        # Price level (0-3 points) - higher price might mean bigger budgets
        price_level = data.get('price_level')
        if price_level:
            score += min(price_level, 3)

        return min(score, 10)

    def _calculate_grade(self, score: float) -> str:
        """
        Calculate letter grade from score.

        Args:
            score: Total score (0-100)

        Returns:
            Letter grade (A+ to F)
        """
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        elif score >= 45:
            return 'D+'
        elif score >= 40:
            return 'D'
        else:
            return 'F'

    def _calculate_priority(self, score: float) -> str:
        """
        Calculate priority level from score.

        Args:
            score: Total score (0-100)

        Returns:
            Priority level
        """
        if score >= 80:
            return 'urgent'
        elif score >= 65:
            return 'high'
        elif score >= 50:
            return 'medium'
        elif score >= 35:
            return 'low'
        else:
            return 'very_low'

    def _generate_score_reasons(self, data: Dict, breakdown: Dict) -> List[str]:
        """
        Generate human-readable reasons for the score.

        Args:
            data: Business data
            breakdown: Score breakdown

        Returns:
            List of reasons
        """
        reasons = []

        # Contact quality reasons
        email_count = len(data.get('emails_found', []))
        if email_count >= 2:
            reasons.append(f"Has {email_count} email addresses")
        elif email_count == 1:
            reasons.append("Has 1 email address")
        else:
            reasons.append("No email addresses found")

        if data.get('phone'):
            reasons.append("Has phone number")

        # Local vs corporate
        franchise_data = data.get('franchise_detection', {})
        if franchise_data.get('is_local'):
            reasons.append("Local independent business")
        elif franchise_data.get('is_franchise'):
            reasons.append(f"Franchise/chain: {franchise_data.get('chain_name', 'Unknown')}")

        # Reputation
        rating = data.get('rating')
        review_count = data.get('user_ratings_total', 0)
        if rating and review_count:
            reasons.append(f"{rating}★ rating with {review_count} reviews")

        # Online presence
        if data.get('website'):
            reasons.append("Has website")

        social_count = len(data.get('social_media', {}))
        if social_count > 0:
            reasons.append(f"Active on {social_count} social platforms")

        # Popular/established
        if data.get('is_popular'):
            reasons.append("Popular/established business")

        return reasons

    def batch_score_leads(self, businesses: List[Dict]) -> List[Dict]:
        """
        Score multiple leads and sort by priority.

        Args:
            businesses: List of business dictionaries

        Returns:
            Sorted list of businesses with scores
        """
        scored = []

        for business in businesses:
            score_data = self.score_lead(business)
            business['lead_score'] = score_data
            scored.append(business)

        # Sort by total score (highest first)
        scored.sort(key=lambda x: x['lead_score']['total'], reverse=True)

        return scored

    def get_top_leads(
        self,
        businesses: List[Dict],
        min_score: float = 50,
        limit: int = None
    ) -> List[Dict]:
        """
        Get top quality leads above a minimum score.

        Args:
            businesses: List of businesses
            min_score: Minimum score threshold
            limit: Maximum number of leads to return

        Returns:
            Filtered and sorted leads
        """
        scored = self.batch_score_leads(businesses)

        # Filter by minimum score
        qualified = [b for b in scored if b['lead_score']['total'] >= min_score]

        if limit:
            qualified = qualified[:limit]

        return qualified
