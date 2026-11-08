"""Preview (or explicitly delete) historical invalid measurement rows."""
import argparse, math
from app.db.session import SessionLocal
from app.models.case import AuditLog, Measurement
EPSILON=1e-6
def invalid(row):
    try:
        a,b=row.start_point,row.end_point
        return row.distance<=EPSILON or math.dist([a[k] for k in("x","y","z")],[b[k] for k in("x","y","z")])<=EPSILON
    except (KeyError,TypeError,ValueError): return True
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--delete-invalid",action="store_true");args=parser.parse_args()
    with SessionLocal.begin() as db:
        rows=db.query(Measurement).all();bad=[row for row in rows if invalid(row)]
        same=sum(1 for row in rows if invalid(row))
        print(f"total={len(rows)} distance<=1e-6={sum(1 for r in rows if r.distance<=EPSILON)} same_or_invalid={same}")
        for row in bad: print(f"id={row.id} versionId={row.case_version_id} createdAt={row.created_at}")
        if args.delete_invalid:
            print(f"deleting={len(bad)}")
            for row in bad:
                db.add(AuditLog(action="MEASUREMENT_INVALID_CLEANED",case_version_id=row.case_version_id,detail={"measurementId":row.id}));db.delete(row)
if __name__=="__main__": main()
