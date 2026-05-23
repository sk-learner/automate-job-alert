import unittest

from job_alerts import Job, is_fresher_software_role


CONFIG = {
    "target_graduation_years": [2026, 2027],
    "preferred_locations": ["india", "bengaluru", "remote"],
    "software_keywords": ["software engineer", "python developer", "sdet"],
    "freshers_keywords": ["fresher", "entry level", "0-1 years", "new graduate", "batch"],
    "reject_keywords": ["senior", "lead", "3+ years", "intern", "contract"],
}


class FresherFilterTests(unittest.TestCase):
    def test_accepts_clear_fresher_software_role(self) -> None:
        job = Job(
            source_id="test:1",
            company="Example MNC",
            title="Associate Software Engineer",
            location="Bengaluru, India",
            url="https://example.com/job",
            description="Entry level role for fresher graduates from the 2026 batch with 0-1 years experience.",
        )
        self.assertTrue(is_fresher_software_role(job, CONFIG))

    def test_rejects_senior_role_even_when_software(self) -> None:
        job = Job(
            source_id="test:2",
            company="Example MNC",
            title="Senior Software Engineer",
            location="Bengaluru, India",
            url="https://example.com/job",
            description="Software engineer role for new graduate programs for the 2026 batch.",
        )
        self.assertFalse(is_fresher_software_role(job, CONFIG))

    def test_rejects_non_software_fresher_role(self) -> None:
        job = Job(
            source_id="test:3",
            company="Example MNC",
            title="Business Analyst",
            location="Remote, India",
            url="https://example.com/job",
            description="Fresher graduates from the 2027 batch can apply.",
        )
        self.assertFalse(is_fresher_software_role(job, CONFIG))

    def test_rejects_roles_outside_preferred_location(self) -> None:
        job = Job(
            source_id="test:4",
            company="Example MNC",
            title="Python Developer",
            location="London",
            url="https://example.com/job",
            description="Entry level software engineer role for 2026 graduates.",
        )
        self.assertFalse(is_fresher_software_role(job, CONFIG))

    def test_rejects_wrong_graduation_year(self) -> None:
        job = Job(
            source_id="test:5",
            company="Example MNC",
            title="Software Engineer",
            location="Bengaluru, India",
            url="https://example.com/job",
            description="Entry level role for fresher graduates from the 2025 batch.",
        )
        self.assertFalse(is_fresher_software_role(job, CONFIG))

    def test_accepts_2027_graduation_year(self) -> None:
        job = Job(
            source_id="test:6",
            company="Example MNC",
            title="Software Engineer",
            location="Bengaluru, India",
            url="https://example.com/job",
            description="Entry level role for fresher graduates from the 2027 batch.",
        )
        self.assertTrue(is_fresher_software_role(job, CONFIG))


if __name__ == "__main__":
    unittest.main()
