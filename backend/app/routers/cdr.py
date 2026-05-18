import io
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_supervisor
from ..database import get_db

router = APIRouter()

CDR_TABLE = "cdr"


def _query_cdr(db: Session, src: str = "", dst: str = "",
               disposition: str = "", date_from: Optional[date] = None,
               date_to: Optional[date] = None, limit: int = 200, offset: int = 0):
    filters = []
    params = {"limit": limit, "offset": offset}

    if src:
        filters.append("src LIKE :src")
        params["src"] = f"%{src}%"
    if dst:
        filters.append("dst LIKE :dst")
        params["dst"] = f"%{dst}%"
    if disposition:
        filters.append("disposition = :disposition")
        params["disposition"] = disposition
    if date_from:
        filters.append("calldate >= :date_from")
        params["date_from"] = date_from
    if date_to:
        filters.append("calldate < :date_to")
        params["date_to"] = date_to

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    sql = text(f"""
        SELECT calldate, src, dst, duration, billsec, disposition,
               uniqueid, recordingfile, clid
        FROM {CDR_TABLE} {where}
        ORDER BY calldate DESC
        LIMIT :limit OFFSET :offset
    """)
    try:
        rows = db.execute(sql, params).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


@router.get("/")
async def list_cdr(
    src: str = "", dst: str = "", disposition: str = "",
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    limit: int = Query(100, le=500), offset: int = 0,
    db: Session = Depends(get_db), _=Depends(require_supervisor),
):
    return _query_cdr(db, src, dst, disposition, date_from, date_to, limit, offset)


@router.get("/stats")
async def cdr_stats(
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    db: Session = Depends(get_db), _=Depends(require_supervisor),
):
    params = {}
    where_parts = []
    if date_from:
        where_parts.append("calldate >= :date_from")
        params["date_from"] = date_from
    if date_to:
        where_parts.append("calldate < :date_to")
        params["date_to"] = date_to
    where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

    try:
        total = db.execute(text(f"SELECT COUNT(*) FROM {CDR_TABLE} {where}"), params).scalar()
        answered = db.execute(
            text(f"SELECT COUNT(*) FROM {CDR_TABLE} {where} {'AND' if where else 'WHERE'} disposition='ANSWERED'"),
            params
        ).scalar() if not where else db.execute(
            text(f"SELECT COUNT(*) FROM {CDR_TABLE} WHERE disposition='ANSWERED' {'AND' if not where_parts else 'AND ' + ' AND '.join(where_parts)}"),
            params
        ).scalar()

        hourly_sql = text(f"""
            SELECT HOUR(calldate) as hour, COUNT(*) as calls
            FROM {CDR_TABLE} {where}
            GROUP BY HOUR(calldate) ORDER BY hour
        """)
        hourly = [dict(r._mapping) for r in db.execute(hourly_sql, params).fetchall()]

        return {
            "total": total,
            "answered": answered,
            "no_answer": total - answered if total else 0,
            "hourly": hourly,
        }
    except Exception as e:
        return {"total": 0, "answered": 0, "no_answer": 0, "hourly": [], "error": str(e)}


@router.get("/export")
async def export_cdr(
    src: str = "", dst: str = "", disposition: str = "",
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    fmt: str = "csv",
    db: Session = Depends(get_db), _=Depends(require_supervisor),
):
    rows = _query_cdr(db, src, dst, disposition, date_from, date_to, limit=10000)

    if fmt == "csv":
        import csv
        output = io.StringIO()
        if rows:
            w = csv.DictWriter(output, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=cdr.csv"},
        )

    # PDF
    try:
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
        from reportlab.lib import colors

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        headers = ["Fecha", "Origen", "Destino", "Duración", "Estado"]
        data = [headers] + [
            [str(r.get("calldate", "")), r.get("src", ""), r.get("dst", ""),
             str(r.get("duration", "")), r.get("disposition", "")]
            for r in rows[:500]
        ]
        t = Table(data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4ff")]),
        ]))
        doc.build([t])
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=cdr.pdf"},
        )
    except ImportError:
        return {"error": "reportlab not available"}
