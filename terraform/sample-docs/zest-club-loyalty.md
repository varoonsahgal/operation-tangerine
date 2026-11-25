# Zest Club Loyalty Program

Zest Club is Citrus & Co.'s free loyalty program.

## Tiers
| Tier | Lifetime spend | Perks |
|---|---|---|
| Peel | $0+ | 1 point per $1, birthday coupon |
| Pulp | $1,000+ | 1.5 points per $1, free express shipping |
| Juice | $5,000+ | 2 points per $1, free express shipping, 45-day returns, priority support line |
| Tangerine | $15,000+ | 3 points per $1, everything in Juice, a dedicated account manager |

Lifetime spend is the `lifetime_value` column in the customers table.

## Redeeming points
100 points = $1 off. Points expire after 18 months of no purchases.

## Enterprise customers
Customers in the `enterprise` segment are automatically placed in at least the Juice tier
and are billed on net-30 invoices instead of card payments.
