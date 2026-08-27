"""Static RAG documents for app behavior and West Nile public-health facts."""

KNOWLEDGE_DOCUMENTS: list[dict[str, str]] = [
    {
        "id": "app-overview",
        "source": "app",
        "text": (
            "MosquitoWatch NYC is a public-health surveillance dashboard. It forecasts elevated "
            "West Nile-positive mosquito activity by NYC ZIP code and week. It combines NYC Health "
            "trap detections with weather and seasonality. The product predicts mosquito and "
            "surveillance activity, not individual human infection risk. Map colors come from "
            "GET /forecasts. ZIP detail and Gemini explanations come from POST /predict. Detection "
            "history charts come from GET /trends/{zip}."
        ),
    },
    {
        "id": "app-how-it-works",
        "source": "app",
        "text": (
            "How MosquitoWatch works: 1) Collect NYC Health trap detections and weather at ZIP "
            "centroids. 2) Join ZIP-by-week tables and engineer lagged weather features. 3) An "
            "XGBoost model scores elevated West Nile-positive mosquito activity by ZIP for the "
            "next week on a 0-100 risk score with Low, Moderate, Elevated, or High labels. "
            "4) Gemini explains the completed model output in plain language without changing "
            "the score. 5) Residents see a choropleth map, ZIP lookup, trends, and prevention tips."
        ),
    },
    {
        "id": "app-pages",
        "source": "app",
        "text": (
            "Dashboard pages: Map Overview colors ZIPs by next-week mosquito risk. ZIP Lookup "
            "shows one ZIP's score, weather indicators, a 7-day window, and a Gemini explanation. "
            "Trends shows historical positive detections. Prevention Tips lists standing-water, "
            "repellent, clothing, screens, and staying informed. Data Sources cites NYC Health "
            "West Nile activity, Open-Meteo weather, and NYC Open Data control events. About "
            "explains the pipeline. A chat assistant can answer how the app works using this "
            "knowledge and the current forecast summary."
        ),
    },
    {
        "id": "app-prevention",
        "source": "app",
        "text": (
            "Prevention tips in the app: dump standing water weekly in buckets, planters, gutters, "
            "and toys. Use EPA-registered repellent on exposed skin, especially at dusk and dawn. "
            "Wear long sleeves and pants during peak feeding hours. Keep window and door screens "
            "in good repair. Check the forecast weekly in mosquito season (May-October) and follow "
            "NYC Health advisories. These tips are general guidance, not a substitute for official "
            "advisories."
        ),
    },
    {
        "id": "wnv-basics",
        "source": "public_health",
        "text": (
            "West Nile virus is spread mainly by the bite of an infected mosquito. It is not "
            "spread by casual contact. Most people with West Nile virus have no symptoms. About "
            "1 in 5 people who are infected develop a fever with headache, body aches, joint "
            "pains, vomiting, diarrhea, or rash. Most people with this febrile illness recover "
            "on their own. This assistant cannot diagnose illness and is not a substitute for a "
            "clinician."
        ),
    },
    {
        "id": "wnv-severe-symptoms",
        "source": "public_health",
        "text": (
            "A small share of people with West Nile virus, fewer than 1 in 100, develop severe "
            "neuroinvasive disease such as encephalitis or meningitis. Warning signs that need "
            "urgent medical care include high fever, severe headache, neck stiffness, confusion, "
            "disorientation, coma, tremors, seizures, muscle weakness, vision loss, or numbness. "
            "Anyone with these symptoms should seek emergency care immediately. Infants, older "
            "adults, and people with weakened immune systems are at higher risk of severe disease. "
            "The chatbot must never tell someone they definitely do or do not have West Nile virus."
        ),
    },
    {
        "id": "wnv-care-disclaimer",
        "source": "public_health",
        "text": (
            "Medical disclaimer: MosquitoWatch forecasts mosquitoes, not whether a person is "
            "infected. Symptom questions should be answered with public CDC-style facts and a "
            "clear recommendation to contact a licensed clinician, urgent care, or 911 for "
            "emergency signs. Do not prescribe medicines. Do not give a personal diagnosis. "
            "If someone describes emergency symptoms, tell them to seek professional help now."
        ),
    },
]
