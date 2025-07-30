from django.db import models

class Job(models.Model):
    JOB_TYPES = [
        ('FULL_TIME', 'Full-time'),
        ('PART_TIME', 'Part-time'),
        ('CONTRACT', 'Contract'),
        ('INTERNSHIP', 'Internship'),
    ]

    company_name = models.CharField(max_length=200)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    role = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    experience_required = models.CharField(max_length=100)
    short_description = models.TextField()
    full_description = models.TextField()
    skills_required = models.JSONField()  # Store as array of strings
    apply_link = models.URLField(max_length=500)
    compensation = models.CharField(max_length=200, blank=True, default='')  # Salary/compensation info
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job_type']),
            models.Index(fields=['location']),
            models.Index(fields=['role']),
            models.Index(fields=['company_name']),
        ]

    def __str__(self):
        return f"{self.role} at {self.company_name}"
