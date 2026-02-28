"""
Autonomous trigger scheduler.

Runs a background thread (started by SimCoreConfig.ready()) that polls
PersonaState records with trigger_active=True and next_trigger_at <= now.
When found, it auto-creates a follow-up Scenario and fires run_simulation().
"""
import threading
import logging
import time

logger = logging.getLogger(__name__)


def fire_scheduled_simulations():
    """Check for due triggers and launch follow-up simulations."""
    from django.utils import timezone
    from .models import PersonaState, Scenario

    now = timezone.now()
    due_states = PersonaState.objects.filter(
        trigger_active=True,
        next_trigger_at__lte=now,
    )

    for ps in due_states:
        # Find the last completed scenario for this persona
        last = (
            Scenario.objects
            .filter(target_persona=ps.persona, persona_state=ps, status='COMPLETED')
            .order_by('-created_at')
            .first()
        )
        if not last:
            continue

        # Disable before firing to prevent double-fire
        ps.trigger_active = False
        ps.next_trigger_at = None
        ps.save()

        new_scenario = Scenario.objects.create(
            domain=last.domain,
            target_persona=last.target_persona,
            persona_state=ps,
            title=f"Follow-up #{last.session_number + 1} — {last.title}",
            persuader_goal=last.persuader_goal,
            context_json=last.context_json,
            session_number=last.session_number + 1,
            status='RUNNING',
            is_autonomous=True,
        )

        logger.info(
            "Scheduler: auto-firing follow-up scenario #%d for persona '%s'",
            new_scenario.id, ps.persona.name,
        )

        from .engine import run_simulation
        t = threading.Thread(target=run_simulation, args=(new_scenario.id,), daemon=True)
        t.start()


def start_scheduler():
    """Start the background polling daemon thread."""
    def _loop():
        while True:
            time.sleep(900)  # poll every 15 minutes
            try:
                fire_scheduled_simulations()
            except Exception as e:
                logger.error("Scheduler error: %s", e)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("Simulation scheduler started (polling every 15 minutes).")
