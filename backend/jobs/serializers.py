from rest_framework import serializers
from .models import Job

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            'id',
            'company_name',
            'job_type',
            'role',
            'location',
            'experience_required',
            'short_description',
            'full_description',
            'skills_required',
            'apply_link',
            'compensation',
            'created_at',
            'updated_at'
        ]
