"""Step 24 reference data shared by every environment.

Native ids start at 1001 so they never collide with the baseline placeholder rows (ids 1-3) in 003_seed.sql.
City coordinates are rounded public-gazetteer values (2 dp), used only for distance-style lookups.
"""

COUNTRY_IN = 1   # baseline country row 'IN'

STATES = [  # (id, ISO 3166-2:IN subdivision code, name)
    (1001, "KA", "Karnataka"), (1002, "MH", "Maharashtra"), (1003, "TG", "Telangana"), (1004, "TN", "Tamil Nadu"),
    (1005, "DL", "Delhi"), (1006, "HR", "Haryana"), (1007, "UP", "Uttar Pradesh"), (1008, "WB", "West Bengal"),
    (1009, "GJ", "Gujarat"), (1010, "RJ", "Rajasthan"), (1011, "KL", "Kerala"), (1012, "CH", "Chandigarh"),
    (1013, "MP", "Madhya Pradesh"), (1014, "OD", "Odisha"), (1015, "AP", "Andhra Pradesh"), (1016, "AS", "Assam"),
    (1017, "UK", "Uttarakhand"), (1018, "PB", "Punjab"), (1019, "CT", "Chhattisgarh"), (1020, "JH", "Jharkhand"),
    (1021, "BR", "Bihar"),
]
_S = {code: sid for sid, code, _ in STATES}

# (id, name, state code, (lat, lon), tier-1, candidate-population weight)
CITIES = [
    (1001, "Bengaluru", "KA", (12.97, 77.59), True, 9.0), (1002, "Mumbai", "MH", (19.08, 72.88), True, 9.0),
    (1003, "Hyderabad", "TG", (17.39, 78.49), True, 7.0), (1004, "Chennai", "TN", (13.08, 80.27), True, 7.0),
    (1005, "Delhi", "DL", (28.61, 77.21), True, 9.0), (1006, "Pune", "MH", (18.52, 73.86), True, 6.0),
    (1007, "Gurugram", "HR", (28.46, 77.03), True, 4.0), (1008, "Noida", "UP", (28.54, 77.39), True, 4.0),
    (1009, "Kolkata", "WB", (22.57, 88.36), False, 4.0), (1010, "Ahmedabad", "GJ", (23.02, 72.57), False, 3.0),
    (1011, "Jaipur", "RJ", (26.91, 75.79), False, 2.0), (1012, "Kochi", "KL", (9.93, 76.27), False, 2.0),
    (1013, "Coimbatore", "TN", (11.02, 76.96), False, 2.0), (1014, "Chandigarh", "CH", (30.73, 76.78), False, 1.5),
    (1015, "Indore", "MP", (22.72, 75.86), False, 1.5), (1016, "Lucknow", "UP", (26.85, 80.95), False, 2.0),
    (1017, "Nagpur", "MH", (21.15, 79.09), False, 1.5), (1018, "Bhubaneswar", "OD", (20.30, 85.82), False, 1.5),
    (1019, "Visakhapatnam", "AP", (17.69, 83.22), False, 1.5), (1020, "Vadodara", "GJ", (22.31, 73.18), False, 1.0),
    (1021, "Surat", "GJ", (21.17, 72.83), False, 1.5), (1022, "Thiruvananthapuram", "KL", (8.52, 76.94), False, 1.0),
    (1023, "Mysuru", "KA", (12.30, 76.64), False, 1.0), (1024, "Madurai", "TN", (9.93, 78.12), False, 1.0),
    (1025, "Mangaluru", "KA", (12.91, 74.86), False, 0.8), (1026, "Nashik", "MH", (20.00, 73.79), False, 0.8),
    (1027, "Bhopal", "MP", (23.26, 77.41), False, 1.0), (1028, "Patna", "BR", (25.59, 85.14), False, 1.0),
    (1029, "Guwahati", "AS", (26.14, 91.74), False, 0.8), (1030, "Dehradun", "UK", (30.32, 78.03), False, 0.6),
    (1031, "Ludhiana", "PB", (30.90, 75.86), False, 0.8), (1032, "Raipur", "CT", (21.25, 81.63), False, 0.6),
    (1033, "Ranchi", "JH", (23.34, 85.31), False, 0.6), (1034, "Vijayawada", "AP", (16.51, 80.65), False, 0.8),
    (1035, "Tiruchirappalli", "TN", (10.79, 78.70), False, 0.6), (1036, "Hubballi", "KA", (15.36, 75.12), False, 0.5),
    (1037, "Aurangabad", "MH", (19.88, 75.34), False, 0.5), (1038, "Jodhpur", "RJ", (26.24, 73.02), False, 0.5),
    (1039, "Kanpur", "UP", (26.45, 80.33), False, 0.8), (1040, "Faridabad", "HR", (28.41, 77.32), False, 0.8),
]

# Mentor job taxonomy (Step 22 sheet 13) with population shares from the family funnel assumptions
FAMILIES = [("IT_DEV", "Software development", 0.25), ("IT_TEST", "Software testing", 0.15),
            ("NONIT_SALES", "Sales", 0.15), ("NONIT_DELIVERY", "Delivery and operations", 0.15),
            ("BLUE_WAREHOUSE", "Warehouse", 0.15), ("BLUE_FIELD", "Field work", 0.15)]

ROLES = [  # (id, family, title, code). job_role has no family column (MGAP-05), so the code carries it.
    (1001, "IT_DEV", "Backend Developer", "it_dev__backend_developer"),
    (1002, "IT_DEV", "Frontend Developer", "it_dev__frontend_developer"),
    (1003, "IT_DEV", "Mobile Developer", "it_dev__mobile_developer"),
    (1004, "IT_DEV", "Data Engineer", "it_dev__data_engineer"),
    (1005, "IT_TEST", "QA Engineer", "it_test__qa_engineer"),
    (1006, "IT_TEST", "Automation Tester", "it_test__automation_tester"),
    (1007, "IT_TEST", "Performance Tester", "it_test__performance_tester"),
    (1008, "NONIT_SALES", "Field Sales Executive", "nonit_sales__field_sales_executive"),
    (1009, "NONIT_SALES", "Inside Sales Associate", "nonit_sales__inside_sales_associate"),
    (1010, "NONIT_SALES", "Key Account Manager", "nonit_sales__key_account_manager"),
    (1011, "NONIT_DELIVERY", "Delivery Manager", "nonit_delivery__delivery_manager"),
    (1012, "NONIT_DELIVERY", "Operations Executive", "nonit_delivery__operations_executive"),
    (1013, "NONIT_DELIVERY", "Customer Support Associate", "nonit_delivery__customer_support_associate"),
    (1014, "BLUE_WAREHOUSE", "Warehouse Associate", "blue_warehouse__warehouse_associate"),
    (1015, "BLUE_WAREHOUSE", "Forklift Operator", "blue_warehouse__forklift_operator"),
    (1016, "BLUE_WAREHOUSE", "Picker Packer", "blue_warehouse__picker_packer"),
    (1017, "BLUE_FIELD", "Delivery Rider", "blue_field__delivery_rider"),
    (1018, "BLUE_FIELD", "Field Technician", "blue_field__field_technician"),
    (1019, "BLUE_FIELD", "Security Guard", "blue_field__security_guard"),
]

INDUSTRIES = [("it_services", "IT services"), ("software_product", "Software products"), ("bfsi", "Banking and finance"),
              ("retail", "Retail"), ("ecommerce", "E-commerce"), ("logistics", "Logistics"),
              ("manufacturing", "Manufacturing"), ("healthcare", "Healthcare"), ("education", "Education"),
              ("telecom", "Telecom"), ("fmcg", "Consumer goods"), ("staffing", "Staffing services")]
INDUSTRY_IDS = {code: 1001 + i for i, (code, _) in enumerate(INDUSTRIES)}

# NFR-013: English, Hindi and Tamil
LANGUAGES = [("en", 0.60), ("hi", 0.25), ("ta", 0.15)]

# Synthetic name parts per language. Combinations are random; none identifies a real person.
NAMES = {
    "en": (["Asha", "Rahul", "Priya", "Arjun", "Neha", "Vikram", "Kavya", "Rohan", "Sneha", "Aditya", "Divya",
            "Karan", "Meera", "Siddharth", "Ananya", "Nikhil", "Pooja", "Varun", "Isha", "Manish"],
           ["Sharma", "Iyer", "Reddy", "Nair", "Gupta", "Patel", "Singh", "Rao", "Das", "Menon", "Joshi",
            "Kulkarni", "Mehta", "Pillai", "Verma", "Bose"]),
    "hi": (["आशा", "राहुल", "प्रिया", "अर्जुन", "नेहा", "विक्रम", "काव्या", "रोहन", "स्नेहा", "आदित्य",
            "दिव्या", "करण"],
           ["शर्मा", "गुप्ता", "सिंह", "वर्मा", "जोशी", "मेहता", "पटेल", "मिश्रा"]),
    "ta": (["ஆஷா", "ராகுல்", "பிரியா", "அர்ஜுன்", "கவ்யா", "விக்ரம்", "மீரா", "சித்தார்த்", "திவ்யா",
            "கார்த்திக்"],
           ["ஐயர்", "பிள்ளை", "நாயர்", "ராஜன்", "சுப்பிரமணியன்", "கிருஷ்ணன்"]),
}


def reference_rows(stamp):
    """Native rows for the reference seed set: {table: (columns, rows)}."""
    return {
        "state": (["id", "country_id", "code", "name", "created_at", "created_by", "updated_at", "updated_by"],
                  [(i, COUNTRY_IN, c, n, stamp, 1, stamp, 1) for i, c, n in STATES]),
        "city": (["id", "state_id", "name", "latitude", "longitude", "coordinate_source",
                  "created_at", "created_by", "updated_at", "updated_by"],
                 [(i, _S[s], n, f"{ll[0]:.2f}", f"{ll[1]:.2f}", "public gazetteer, rounded 2dp",
                   stamp, 1, stamp, 1) for i, n, s, ll, _, _ in CITIES]),
        "job_role": (["id", "code", "name", "created_at", "created_by", "updated_at", "updated_by"],
                     [(i, code, title, stamp, 1, stamp, 1) for i, _, title, code in ROLES]),
        "industry": (["id", "code", "name", "created_at", "created_by", "updated_at", "updated_by"],
                     [(INDUSTRY_IDS[c], c, n, stamp, 1, stamp, 1) for c, n in INDUSTRIES]),
    }
