"""Seed local reproducible sin afirmaciones comerciales no verificadas."""

import argparse
from datetime import date, datetime, timezone
from pathlib import Path

from opportunity_control.application import OpportunityRepository
from opportunity_control.domain import (
    Account,
    AuditEvent,
    ConfidenceState,
    DecisionOption,
    EventOutcome,
    Evidence,
    Hypothesis,
    NextAction,
    Opportunity,
    OpportunityStage,
    Unknown,
)
from opportunity_control.domain.accounts import Contact
from opportunity_control.domain.opportunities import Signal
from opportunity_control.infrastructure import (
    SQLiteOpportunityRepository,
    connect_database,
    initialize_database,
)

SEED_CASES: tuple[tuple[Account, Opportunity], ...] = (
    (
        Account(id="ACCOUNT-UVA", name="UVA"),
        Opportunity(
            id="OPPORTUNITY-UVA-AI-PILOT",
            account_id="ACCOUNT-UVA",
            title="UVA × Bridgelytic — Applied AI pilot",
            owner="synthetic-owner",
        ),
    ),
    (
        Account(id="ACCOUNT-X-HUMANOID", name="X-Humanoid"),
        Opportunity(
            id="OPPORTUNITY-X-HUMANOID-NA",
            account_id="ACCOUNT-X-HUMANOID",
            title="X-Humanoid — North America commercialization",
            owner="synthetic-owner",
        ),
    ),
    (
        Account(id="ACCOUNT-BOOSTER", name="Booster Robotics"),
        Opportunity(
            id="OPPORTUNITY-BOOSTER-PILOTS",
            account_id="ACCOUNT-BOOSTER",
            title="Booster Robotics — university / commercialization pilots",
            owner="synthetic-owner",
        ),
    ),
)


def seed_repository(repository: OpportunityRepository) -> None:
    """Carga tres casos mínimos y registra su creación en auditoría."""

    occurred_at = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    with repository.transaction():
        for index, (account, opportunity) in enumerate(SEED_CASES, start=1):
            repository.add_account(account)
            repository.add_opportunity(opportunity)
            repository.add_contact(
                Contact(
                    f"CONTACT-SEED-{index:03d}",
                    account.id,
                    "Responsable técnico ficticio",
                    "Rol de prueba; identidad real pendiente",
                )
            )
            repository.add_signal(
                Signal(
                    id=f"SIGNAL-SEED-{index:03d}",
                    account_id=account.id,
                    title="Solicitud ficticia de evaluar un caso en entorno local",
                    observed_at=occurred_at.date(),
                    opportunity_id=opportunity.id,
                    source=f"data/SEED_SOURCES.md#caso-{index}",
                    provenance="Fixture escrito para pruebas; no es actividad real de la organización",
                )
            )
            repository.add_evidence(
                Evidence(
                    id=f"EVIDENCE-SEED-{index:03d}",
                    opportunity_id=opportunity.id,
                    statement=f"El fixture del caso {index} exige una evaluación local sin ejecución externa.",
                    source=f"data/SEED_SOURCES.md#caso-{index}",
                    provenance="VERIFIED sólo frente al fixture; no verifica una oportunidad comercial real",
                    confidence_state=ConfidenceState.VERIFIED,
                    confidence=1.0,
                    recorded_at=occurred_at,
                )
            )
            for option_number, (title, rationale, risk) in enumerate(
                (
                    (
                        "Preparar evaluación interna acotada",
                        "Permite revisar supuestos con el fixture disponible.",
                        "El resultado sintético no demuestra viabilidad comercial real.",
                    ),
                    (
                        "Esperar evidencia sanitizada adicional",
                        "Evita concluir sobre información aún no entregada.",
                        "Se retrasa la evaluación, pero no se compromete a ninguna organización.",
                    ),
                ),
                start=1,
            ):
                repository.add_decision_option(
                    DecisionOption(
                        f"OPTION-SEED-{index:03d}-{option_number}",
                        opportunity.id,
                        title,
                        rationale,
                        risk,
                    )
                )
            repository.add_hypothesis(
                Hypothesis(
                    id=f"HYPOTHESIS-SEED-{index:03d}",
                    opportunity_id=opportunity.id,
                    statement="Hipótesis sintética pendiente de validación.",
                    rationale="Fixture local para demostrar separación de datos.",
                    confidence=0.4,
                )
            )
            repository.add_unknown(
                Unknown(
                    id=f"UNKNOWN-SEED-{index:03d}",
                    opportunity_id=opportunity.id,
                    question="¿Qué evidencia sanitizada confirmará esta oportunidad?",
                )
            )
            repository.add_next_action(
                NextAction(
                    id=f"ACTION-SEED-{index:03d}",
                    opportunity_id=opportunity.id,
                    description="Revisar el dataset sanitizado cuando sea entregado.",
                    owner="synthetic-owner",
                    due_date=date(2026, 9, 30),
                )
            )
            repository.append_audit_event(
                AuditEvent(
                    id=f"AUDIT-SEED-{index:03d}",
                    opportunity_id=opportunity.id,
                    event_type="OPPORTUNITY_SEEDED",
                    actor="local-seed",
                    occurred_at=occurred_at,
                    outcome=EventOutcome.ACCEPTED,
                    next_stage=OpportunityStage.INTAKE,
                    detail=(
                        f"Fixture sintético v2; caso {index}: cuenta, oportunidad, contacto, señal, "
                        "evidencia, hipótesis, incógnita, dos opciones y next action creados juntos. "
                        "No representa evidencia comercial ni aprobación humana."
                    ),
                )
            )


def create_seed_database(
    database_path: str | Path,
    *,
    replace: bool = False,
) -> None:
    """Crea una base nueva; el argumento legado replace no autoriza borrados."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        # Un seed no debe borrar el trabajo anterior, aunque se invoque por accidente.
        raise FileExistsError(
            "La base ya existe. Elija otra ruta para un seed nuevo; no se borra el historial."
        )

    connection = connect_database(path)
    try:
        initialize_database(connection)
        seed_repository(SQLiteOpportunityRepository(connection))
    finally:
        connection.close()


def main() -> None:
    """Genera la base de demostración dentro de `runtime/`."""

    parser = argparse.ArgumentParser(
        description="Crear un dataset sintético sin sobrescribir bases"
    )
    parser.add_argument("--database", type=Path, default=Path("runtime/demo.db"))
    database_path = parser.parse_args().database
    create_seed_database(database_path)
    print(f"Base sintética creada en {database_path}")


if __name__ == "__main__":
    main()
