from enum import StrEnum


class LifecycleState(StrEnum):
    NEW = "new"
    ENRICHED = "enriched"
    SCORED = "scored"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"
    NO_REPLY = "no_reply"
    WARM_REPLY = "warm_reply"
    COLD_REPLY = "cold_reply"
    AUTO_RESPONDED = "auto_responded"
    CONVERTED = "converted"
    LOST = "lost"


VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.NEW: {LifecycleState.ENRICHED, LifecycleState.REJECTED},
    LifecycleState.ENRICHED: {LifecycleState.SCORED, LifecycleState.REJECTED},
    LifecycleState.SCORED: {LifecycleState.AWAITING_REVIEW, LifecycleState.REJECTED},
    LifecycleState.AWAITING_REVIEW: {LifecycleState.APPROVED, LifecycleState.REJECTED},
    LifecycleState.APPROVED: {LifecycleState.SENT},
    LifecycleState.REJECTED: set(),
    LifecycleState.SENT: {LifecycleState.NO_REPLY, LifecycleState.WARM_REPLY, LifecycleState.COLD_REPLY},
    LifecycleState.NO_REPLY: {LifecycleState.SENT, LifecycleState.LOST},
    LifecycleState.WARM_REPLY: {LifecycleState.AUTO_RESPONDED, LifecycleState.CONVERTED},
    LifecycleState.AUTO_RESPONDED: {LifecycleState.WARM_REPLY, LifecycleState.CONVERTED, LifecycleState.AWAITING_REVIEW},
    LifecycleState.COLD_REPLY: {LifecycleState.LOST, LifecycleState.AWAITING_REVIEW},
    LifecycleState.CONVERTED: set(),
    LifecycleState.LOST: set(),
}


def can_transition(from_state: LifecycleState, to_state: LifecycleState) -> bool:
    return to_state in VALID_TRANSITIONS.get(from_state, set())
