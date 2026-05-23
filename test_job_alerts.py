import unittest

from job_alerts import Job, is_fresher_software_role, score_personalized_match


CONFIG = {
    "minimum_match_score": 45,
    "high_match_score": 75,
    "priority_companies": ["TCS", "Cognizant", "Wipro"],
    "trusted_domains": ["tcs.com", "careers.cognizant.com", "fresherdoor.in"],
    "profile": {
        "degrees": ["m.tech", "mtech", "me/mtech"],
        "skills": ["java", "python", "sql", "full stack"],
    },
    "target_graduation_years": [2026, 2027],
    "preferred_locations": ["india", "bengaluru", "remote"],
    "software_keywords": ["software engineer", "python developer", "sdet"],
    "freshers_keywords": ["fresher", "entry level", "0-1 years", "new graduate", "batch"],
    "role_program_keywords": ["tcs nqt", "genc", "java full stack engineer", "project engineer"],
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

    def test_scores_tcs_nqt_mtech_match_even_without_software_title(self) -> None:
        job = Job(
            source_id="test:7",
            company="TCS",
            title="TCS All India NQT Hiring - Prime and Digital",
            location="India",
            url="https://www.tcs.com/careers/india/tcs-all-india-nqt-hiring",
            description=(
                "TCS NQT hiring for the batch of 2024, 2025 and 2026. "
                "Open to B.Tech, M.Tech, MCA and M.Sc candidates."
            ),
        )
        match = score_personalized_match(job, CONFIG)
        self.assertIsNotNone(match)
        self.assertEqual(match.confidence, "High match")

    def test_scores_cognizant_2027_java_fse_match(self) -> None:
        job = Job(
            source_id="test:8",
            company="Cognizant",
            title="Cognizant Digital Nurture 5.0 Java FSE",
            location="India",
            url="https://fresherdoor.in/jobs/cognizant-digital-nurture",
            description=(
                "Entry Level Java Full Stack Engineer for BE/B.Tech/ME/M.Tech. "
                "Batch: 2027. Skills include Java, SQL, cloud and full stack."
            ),
        )
        match = score_personalized_match(job, CONFIG)
        self.assertIsNotNone(match)
        self.assertIn(match.confidence, {"High match", "Medium match"})

    def test_personalized_scoring_rejects_senior_role(self) -> None:
        job = Job(
            source_id="test:9",
            company="TCS",
            title="Senior Software Engineer",
            location="India",
            url="https://www.tcs.com/careers/job",
            description="Hiring for 2026 batch and M.Tech graduates.",
        )
        self.assertIsNone(score_personalized_match(job, CONFIG))


if __name__ == "__main__":
    unittest.main()
