"""Minimal 2D frontend for the NEXUS TECH simulation."""

from nexus_tech.frontend_2d.animation_audit import (
    DEFAULT_ANIMATION_AUDIT_SIZES,
    AnimationAuditReport,
    AnimationCoverageCell,
    run_2d_animation_audit,
)
from nexus_tech.frontend_2d.app import (
    Frontend2DUnavailableError,
    FrontendRunResult,
    launch_2d_frontend,
    launch_2d_menu,
)
from nexus_tech.frontend_2d.motion_audit import (
    DEFAULT_MOTION_AUDIT_SIZES,
    FlowAuditFinding,
    FlowAuditReport,
    MotionAuditCell,
    MotionAuditReport,
    run_2d_flow_audit,
    run_2d_motion_audit,
)
from nexus_tech.frontend_2d.tween import MotionMode, normalize_motion_mode
from nexus_tech.frontend_2d.visual_audit import (
    DEFAULT_VISUAL_AUDIT_SIZES,
    VisualAuditCell,
    VisualAuditReport,
    run_2d_visual_audit,
)

__all__ = [
    "DEFAULT_ANIMATION_AUDIT_SIZES",
    "DEFAULT_MOTION_AUDIT_SIZES",
    "DEFAULT_VISUAL_AUDIT_SIZES",
    "AnimationAuditReport",
    "AnimationCoverageCell",
    "FlowAuditFinding",
    "FlowAuditReport",
    "Frontend2DUnavailableError",
    "FrontendRunResult",
    "MotionMode",
    "MotionAuditCell",
    "MotionAuditReport",
    "launch_2d_frontend",
    "launch_2d_menu",
    "normalize_motion_mode",
    "run_2d_animation_audit",
    "run_2d_flow_audit",
    "run_2d_motion_audit",
    "run_2d_visual_audit",
    "VisualAuditCell",
    "VisualAuditReport",
]
