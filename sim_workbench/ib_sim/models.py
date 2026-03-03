from django.db import models
import json

class Scenario(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    banker_idea = models.TextField(help_text="The idea the banker wants to propose.")
    client_persona = models.TextField(help_text="JSON representation or description of the client persona.")
    client_industry = models.CharField(max_length=100, default="General", help_text="Industry of the client (e.g. Technology, Manufacturing)")
    financial_context = models.TextField(default="Stable financials", help_text="Key financial data (Revenue, eBook, etc.)")
    market_conditions = models.TextField(default="Neutral market", help_text="Current market environment (e.g. Bull/Bear, high interest rates)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CREATED')
    conversation_log = models.TextField(default='[]', help_text="JSON list of conversation turns.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_conversation_log(self, log_list):
        self.conversation_log = json.dumps(log_list)

    def get_conversation_log(self):
        try:
            return json.loads(self.conversation_log)
        except json.JSONDecodeError:
            return []

    def __str__(self):
        return f"Scenario {self.id}: {self.banker_idea[:50]}..."
