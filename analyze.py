import pandas as pd

df = pd.read_csv("population_report.csv")

# Show the ten largest populations in the report.
top_ten = df.nlargest(22, "latest_population")

print("Top 10 populations:")
print(
    top_ten[["country", "latest_year", "latest_population"]]
    .to_string(index=False)
)

# Calculate the average percentage change, ignoring missing values.
average_change = df["change_percent"].mean()
print(f"\nAverage reported change: {average_change:.2f}%")

# Save a smaller file containing countries with positive change.
growing = df[df["change_percent"] > 0]
growing.to_csv("growing_countries.csv", index=False)

print(f"Saved {len(growing)} rows to growing_countries.csv")

