"""
Seed 5 demo DMAs with realistic Moroccan city GeoJSON polygons.

Usage (from api/ directory with venv active):
    python ../scripts/seed_dma_geometry.py --tenant <slug>

The script UPSERTs DMAs and patches their geometry via ST_GeomFromGeoJSON.
Requires a running PostgreSQL instance with PostGIS enabled.
"""
import argparse
import asyncio
import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)) + "/api")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://tanqit:tanqit@localhost:5432/tanqitflow"
)

# Five demo DMAs centred on Moroccan cities (simplified bounding rectangles)
DEMO_DMAS = [
    {
        "code": "DMA-RABAT-01",
        "name": "Rabat Nord",
        "zone": "Rabat-Salé",
        "pipe_length_km": 28.4,
        "connection_count": 3200,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-6.870, 34.030], [-6.820, 34.030],
                [-6.820, 33.990], [-6.870, 33.990],
                [-6.870, 34.030],
            ]],
        },
        "nrw_pct": 18.2,
        "flag": "normal",
    },
    {
        "code": "DMA-CASA-01",
        "name": "Casablanca Centre",
        "zone": "Grand Casablanca",
        "pipe_length_km": 42.1,
        "connection_count": 7800,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-7.640, 33.600], [-7.580, 33.600],
                [-7.580, 33.560], [-7.640, 33.560],
                [-7.640, 33.600],
            ]],
        },
        "nrw_pct": 27.5,
        "flag": "warning",
    },
    {
        "code": "DMA-FES-01",
        "name": "Fès Médina",
        "zone": "Fès-Meknès",
        "pipe_length_km": 19.7,
        "connection_count": 2100,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-5.010, 34.070], [-4.960, 34.070],
                [-4.960, 34.040], [-5.010, 34.040],
                [-5.010, 34.070],
            ]],
        },
        "nrw_pct": 44.8,
        "flag": "critical",
    },
    {
        "code": "DMA-MARR-01",
        "name": "Marrakech Guéliz",
        "zone": "Marrakech-Safi",
        "pipe_length_km": 33.6,
        "connection_count": 4500,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-8.020, 31.650], [-7.970, 31.650],
                [-7.970, 31.610], [-8.020, 31.610],
                [-8.020, 31.650],
            ]],
        },
        "nrw_pct": 31.1,
        "flag": "warning",
    },
    {
        "code": "DMA-TANG-01",
        "name": "Tanger Port",
        "zone": "Tanger-Tétouan",
        "pipe_length_km": 15.3,
        "connection_count": 1850,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-5.820, 35.790], [-5.780, 35.790],
                [-5.780, 35.760], [-5.820, 35.760],
                [-5.820, 35.790],
            ]],
        },
        "nrw_pct": 22.0,
        "flag": "normal",
    },
]


async def seed(tenant: str) -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Set tenant search path
        await db.execute(text(f"SET search_path TO {tenant}, public"))

        for dma in DEMO_DMAS:
            # Upsert the DMA row
            await db.execute(text("""
                INSERT INTO dma (code, name, zone, pipe_length_km, connection_count, is_active)
                VALUES (:code, :name, :zone, :plkm, :cc, true)
                ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name,
                        zone = EXCLUDED.zone,
                        pipe_length_km = EXCLUDED.pipe_length_km,
                        connection_count = EXCLUDED.connection_count,
                        updated_at = NOW()
            """), {
                "code": dma["code"],
                "name": dma["name"],
                "zone": dma["zone"],
                "plkm": dma["pipe_length_km"],
                "cc": dma["connection_count"],
            })

            # Patch geometry
            await db.execute(text("""
                UPDATE dma
                SET geometry = ST_GeomFromGeoJSON(:geom)
                WHERE code = :code
            """), {"geom": json.dumps(dma["geometry"]), "code": dma["code"]})

            # Upsert a recent balance period so the map shows NRW colours
            await db.execute(text("""
                INSERT INTO balance_period
                    (dma_code, period_start, period_end, siv_m3, scv_m3, nrw_m3, nrw_pct, flag_level)
                VALUES (
                    :code,
                    date_trunc('month', NOW() - INTERVAL '1 month'),
                    date_trunc('month', NOW()),
                    10000,
                    :scv,
                    :nrw_m3,
                    :nrw_pct,
                    :flag
                )
                ON CONFLICT (dma_code, period_start) DO UPDATE
                    SET nrw_pct = EXCLUDED.nrw_pct,
                        flag_level = EXCLUDED.flag_level
            """), {
                "code": dma["code"],
                "nrw_pct": dma["nrw_pct"],
                "nrw_m3": 10000 * dma["nrw_pct"] / 100,
                "scv": 10000 * (1 - dma["nrw_pct"] / 100),
                "flag": dma["flag"],
            })

            print(f"  ✓ {dma['code']} — {dma['name']} ({dma['flag']})")

        await db.commit()

    await engine.dispose()
    print(f"\nSeeded {len(DEMO_DMAS)} DMAs into tenant '{tenant}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True, help="Tenant slug (e.g. demo)")
    args = parser.parse_args()
    asyncio.run(seed(args.tenant))
