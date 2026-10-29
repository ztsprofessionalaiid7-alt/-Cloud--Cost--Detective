import random
from datetime import date, timedelta
import pandas as pd

random.seed(42)

SERVICES = {
    "EC2": ("Compute", 42),
    "Lambda": ("Compute", 6),
    "S3": ("Storage", 12),
    "RDS": ("Database", 30),
    "CloudFront": ("Network", 9),
}
REGIONS = {"us-east-1": 1.0, "eu-west-1": 0.6}
START = date(2026, 9, 1)

rows = []
for d in range(30):
    day = START + timedelta(days=d)
    for svc, (cat, base) in SERVICES.items():
        for reg, factor in REGIONS.items():
            cost = base * factor * random.uniform(0.9, 1.1)
            # ইচ্ছাকৃত স্পাইক ১: EC2 হঠাৎ ৩.৫ গুণ
            if svc == "EC2" and reg == "us-east-1" and 20 <= d <= 23:
                cost *= 3.5
            # ইচ্ছাকৃত স্পাইক ২: S3 ধীরে ধীরে বাড়ছে
            if svc == "S3" and d >= 25:
                cost *= 2.2
            rows.append([day.isoformat(), svc, cat, reg, round(cost, 2), "USD"])
    # নতুন service: আগে কোনো baseline নেই
    if d >= 15:
        rows.append([day.isoformat(), "SageMaker", "AI/ML", "us-east-1",
                     round(25 * random.uniform(0.9, 1.1), 2), "USD"])

df = pd.DataFrame(rows, columns=["date", "service", "category", "region", "cost", "currency"])
df.to_csv("data/sample_billing.csv", index=False)
print(f"{len(df)} সারি তৈরি হয়েছে -> data/sample_billing.csv")