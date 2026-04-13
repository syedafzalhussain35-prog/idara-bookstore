import csv
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from store.models import MockTestSubject, MockTestTopic, MockTestQuestion


class Command(BaseCommand):
    help = "Import mock test questions from CSV"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, help="Path to CSV file")
        parser.add_argument("--published", action="store_true", help="Mark imported questions as published")
        parser.add_argument("--export-template", type=str, help="Write CSV template to this file path")

    def handle(self, *args, **options):
        template_path = options.get("export_template")
        if template_path:
            self._export_template(template_path)
            self.stdout.write(self.style.SUCCESS(f"Template exported: {template_path}"))
            return

        path = options.get("file")
        if not path:
            raise CommandError("Provide --file for import or --export-template for template output.")

        status = "published" if options.get("published") else "draft"
        created = 0
        updated = 0

        with open(path, "r", encoding="utf-8-sig", newline="") as fp:
            reader = csv.DictReader(fp)
            required = {
                "question",
                "option_a",
                "option_b",
                "option_c",
                "option_d",
                "correct_option",
                "explanation",
                "subject",
                "topic",
                "difficulty",
            }
            headers = {str(h or "").strip().lower() for h in (reader.fieldnames or [])}
            missing = required - headers
            if missing:
                raise CommandError(f"Missing required columns: {', '.join(sorted(missing))}")

            for idx, row in enumerate(reader, start=2):
                question_text = (row.get("question") or "").strip()
                if not question_text:
                    continue

                subject_name = (row.get("subject") or "General").strip() or "General"
                topic_name = (row.get("topic") or "General").strip() or "General"
                difficulty = (row.get("difficulty") or "medium").strip().lower()
                if difficulty not in {"easy", "medium", "hard"}:
                    difficulty = "medium"

                correct_option = (row.get("correct_option") or "").strip().upper()
                if correct_option not in {"A", "B", "C", "D"}:
                    self.stdout.write(self.style.WARNING(f"Row {idx}: invalid correct_option '{correct_option}', skipped"))
                    continue

                subject, _ = MockTestSubject.objects.get_or_create(name=subject_name)
                if not subject.slug:
                    subject.slug = slugify(subject.name)
                    subject.save(update_fields=["slug"])

                topic, _ = MockTestTopic.objects.get_or_create(subject=subject, name=topic_name)
                if not topic.slug:
                    topic.slug = slugify(topic.name)
                    topic.save(update_fields=["slug"])

                payload = {
                    "option_a": (row.get("option_a") or "").strip(),
                    "option_b": (row.get("option_b") or "").strip(),
                    "option_c": (row.get("option_c") or "").strip(),
                    "option_d": (row.get("option_d") or "").strip(),
                    "correct_option": correct_option,
                    "explanation_short": (row.get("explanation") or "").strip(),
                    "explanation_detailed": (row.get("explanation_detailed") or "").strip(),
                    "memory_trick": (row.get("memory_trick") or "").strip(),
                    "key_concept": (row.get("key_concept") or "").strip(),
                    "reference_source": (row.get("reference_source") or "").strip(),
                    "tags": (row.get("tags") or "").strip(),
                    "difficulty": difficulty,
                    "is_previous_year": str(row.get("is_previous_year") or "").strip().lower() in {"1", "true", "yes", "y"},
                    "status": status,
                    "is_active": True,
                    "subject": subject,
                    "topic": topic,
                }

                obj, was_created = MockTestQuestion.objects.update_or_create(
                    question_text=question_text,
                    subject=subject,
                    topic=topic,
                    defaults=payload,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Import complete. Created={created}, Updated={updated}, Status={status}"))

    def _export_template(self, template_path):
        headers = [
            "question",
            "option_a",
            "option_b",
            "option_c",
            "option_d",
            "correct_option",
            "explanation",
            "explanation_detailed",
            "memory_trick",
            "subject",
            "topic",
            "difficulty",
            "key_concept",
            "reference_source",
            "tags",
            "is_previous_year",
        ]
        with open(template_path, "w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(headers)
            writer.writerow([
                "Example question text",
                "Option A",
                "Option B",
                "Option C",
                "Option D",
                "A",
                "Short explanation",
                "Detailed explanation",
                "Memory trick",
                "Kulliyat",
                "Mizaj",
                "medium",
                "Concept name",
                "Reference text",
                "tag1,tag2",
                "false",
            ])
