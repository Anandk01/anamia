"""
rag_knowledge.py — Static RAG knowledge base from WHO and NHLBI sources.

Sources:
  - WHO Anaemia Fact Sheet: https://www.who.int/news-room/fact-sheets/detail/anaemia
  - NHLBI Iron-Deficiency Anemia: https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia
  - NHLBI Anemia Treatment: https://www.nhlbi.nih.gov/health/anemia/treatment

Content was fetched and embedded as a static knowledge base for RAG.
"""

# ---------------------------------------------------------------------------
# Knowledge chunks — each chunk is a dict with source, topic, and content
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE = [
    {
        "source": "WHO Anaemia Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "topic": "definition",
        "content": (
            "Anaemia is a condition in which the number of red blood cells or the haemoglobin "
            "concentration within them is lower than normal. It mainly affects women and children. "
            "Anaemia occurs when there isn't enough haemoglobin in the body to carry oxygen to the "
            "organs and tissues. In severe cases, anaemia can cause poor cognitive and motor "
            "development in children. It can also cause problems for pregnant women and their babies."
        ),
    },
    {
        "source": "WHO Anaemia Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "topic": "causes",
        "content": (
            "Anaemia can be caused by poor nutrition, infections, chronic diseases, heavy menstruation, "
            "pregnancy issues and family history. It is often caused by a lack of iron in the blood. "
            "Iron deficiency, primarily due to inadequate dietary iron intake, is considered the most "
            "common nutritional deficiency leading to anaemia. Deficiencies in vitamin A, folate, "
            "vitamin B12 and riboflavin can also result in anaemia. Additional causes include blood "
            "loss from parasitic infections, haemorrhage associated with childbirth, or menstrual loss, "
            "impaired absorption, and low iron stores at birth."
        ),
    },
    {
        "source": "WHO Anaemia Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "topic": "symptoms",
        "content": (
            "Anaemia causes symptoms such as fatigue, reduced physical work capacity, and shortness of "
            "breath. Common and non-specific symptoms include: tiredness, dizziness or feeling "
            "light-headed, cold hands and feet, headache, shortness of breath especially upon exertion. "
            "Severe anaemia can cause: pale mucous membranes, pale skin and under the fingernails, "
            "rapid breathing and heart rate, dizziness when standing up, bruising more easily."
        ),
    },
    {
        "source": "WHO Anaemia Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "topic": "diet_treatment",
        "content": (
            "Changes in diet can help reduce anaemia. Recommended dietary actions include: "
            "eating foods that are rich in iron, folate, vitamin B12, vitamin A, and other nutrients; "
            "eating a healthy diet with a variety of foods; taking supplements if a qualified "
            "health-care provider recommends them. "
            "To keep a healthy and diverse diet: eat iron-rich foods, including lean red meats, fish "
            "and poultry, legumes (e.g. lentils and beans), fortified cereals and dark green leafy "
            "vegetables; eat foods rich in vitamin C (such as fruits and vegetables) which help the "
            "body absorb iron; avoid foods that slow down iron absorption when consuming iron-rich "
            "foods, such as bran in cereals (wholewheat flour, oats), tea, coffee, cocoa and calcium. "
            "If you take calcium and iron supplements, take them at different times during the day."
        ),
    },
    {
        "source": "WHO Anaemia Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "topic": "prevention",
        "content": (
            "Anaemia is preventable and treatable. Prevention includes: prevent and treat malaria; "
            "prevent and treat schistosomiasis and other infections; get vaccinated and practice good "
            "hygiene; manage chronic diseases like obesity and digestive problems; wait at least 24 "
            "months between pregnancies; prevent and treat heavy menstrual bleeding; treat inherited "
            "red blood cell disorders like sickle-cell disease and thalassemia."
        ),
    },
    {
        "source": "WHO Anaemia Fact Sheet",
        "url": "https://www.who.int/news-room/fact-sheets/detail/anaemia",
        "topic": "global_impact",
        "content": (
            "Anaemia is estimated to affect half a billion women 15–49 years of age and 269 million "
            "children 6–59 months of age worldwide. In 2019, 30% (539 million) of non-pregnant women "
            "and 37% (32 million) of pregnant women aged 15–49 years were affected by anaemia. "
            "The WHO Regions of Africa and South-East Asia are most affected. Anaemia can affect "
            "school performance, productivity in adult life, and overall quality of life. During "
            "pregnancy, anaemia has been associated with premature birth, low birth weight and "
            "maternal mortality."
        ),
    },
    {
        "source": "NHLBI Iron-Deficiency Anemia",
        "url": "https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia",
        "topic": "iron_deficiency_definition",
        "content": (
            "Iron-deficiency anemia is a type of anemia that develops if you do not have enough iron "
            "in your body. It is the most common type of anemia. Your body needs iron to make healthy "
            "red blood cells. People with mild or moderate iron-deficiency anemia may not have any "
            "symptoms. More serious iron-deficiency anemia may cause tiredness, shortness of breath, "
            "or chest pain. Other symptoms include fatigue, dizziness or lightheadedness, cold hands "
            "and feet, and pale skin."
        ),
    },
    {
        "source": "NHLBI Iron-Deficiency Anemia",
        "url": "https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia",
        "topic": "iron_deficiency_causes",
        "content": (
            "Conditions that increase risk of iron-deficiency anemia include blood loss (from GI tract "
            "bleeding, traumatic injuries, heavy menstrual periods, regular use of aspirin or NSAIDs, "
            "urinary tract bleeding), problems absorbing iron (celiac disease, ulcerative colitis, "
            "Crohn's disease, stomach surgery), and other medical conditions (kidney disease, "
            "long-lasting conditions that lead to inflammation like congestive heart failure or obesity). "
            "Young children can develop iron-deficiency anemia if they do not get enough iron in their "
            "diet, usually between ages 9 months and 1 year."
        ),
    },
    {
        "source": "NHLBI Iron-Deficiency Anemia",
        "url": "https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia",
        "topic": "iron_deficiency_diet",
        "content": (
            "Good sources of iron include: beans, dried fruits, eggs, lean red meat, salmon, "
            "iron-fortified breads and cereals, peas, tofu, and dark green leafy vegetables. "
            "Vitamin C-rich foods such as oranges, strawberries, and tomatoes help your body absorb "
            "iron. A diet that includes these foods will provide the iron level that your body needs. "
            "Ensure that toddlers eat enough solid foods that are rich in iron. "
            "Some foods like black tea can reduce iron absorption."
        ),
    },
    {
        "source": "NHLBI Iron-Deficiency Anemia",
        "url": "https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia",
        "topic": "iron_deficiency_treatment",
        "content": (
            "Treatments for iron-deficiency anemia include: iron supplements (oral iron pills) — the "
            "most common treatment, often takes 3–6 months to restore iron levels; intravenous (IV) "
            "iron for serious cases or long-term conditions; medicines such as erythropoiesis "
            "stimulating agents (ESA) for people with kidney disease; blood transfusions for serious "
            "cases; surgery to stop internal bleeding. "
            "Your doctor may ask you to choose iron-rich foods such as beans, dried fruits, eggs, "
            "lean red meat, salmon, iron-fortified breads and cereals, peas, tofu, and dark green "
            "leafy vegetables. Foods rich in vitamin C help your body absorb iron."
        ),
    },
    {
        "source": "NHLBI Iron-Deficiency Anemia",
        "url": "https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia",
        "topic": "complications",
        "content": (
            "Undiagnosed or untreated iron-deficiency anemia may cause serious complications such as "
            "fatigue, headaches, restless legs syndrome, heart problems, pregnancy complications, and "
            "developmental delays in children. Iron-deficiency anemia can also make other chronic "
            "conditions worse or cause their treatments to work poorly."
        ),
    },
    {
        "source": "NHLBI Anemia Treatment",
        "url": "https://www.nhlbi.nih.gov/health/anemia/treatment",
        "topic": "blood_transfusion",
        "content": (
            "A blood transfusion is a common, safe medical procedure in which healthy blood is given "
            "through an IV line. Blood transfusions replace blood that is lost through surgery or "
            "injury, or provide blood if your body is not making it properly. Transfusions help people "
            "with serious anemia quickly increase the number of red blood cells. Your doctor may "
            "recommend this if you have serious complications of anemia. Blood transfusions are usually "
            "very safe because donated blood is carefully tested, handled, and stored."
        ),
    },
    {
        "source": "NHLBI Anemia Treatment",
        "url": "https://www.nhlbi.nih.gov/health/anemia/treatment",
        "topic": "bone_marrow_transplant",
        "content": (
            "A bone marrow transplant (hematopoietic stem cell transplant) replaces faulty "
            "blood-forming stem cells with healthy cells. It is usually performed in a hospital. "
            "When healthy stem cells come from the patient, it is called an autologous transplant. "
            "When from another person, it is an allogeneic transplant. Although effective for some "
            "conditions, the procedure can cause complications including nausea, vomiting, diarrhea, "
            "tiredness, mouth sores, skin rashes, hair loss, and liver damage."
        ),
    },
]


def get_relevant_chunks(query: str, max_chunks: int = 5) -> list:
    """
    Simple keyword-based retrieval from the knowledge base.
    Returns the most relevant chunks for the given query.
    """
    query_lower = query.lower()

    # Score each chunk by keyword overlap
    scored = []
    keywords = query_lower.split()

    for chunk in KNOWLEDGE_BASE:
        content_lower = chunk["content"].lower()
        topic_lower = chunk["topic"].lower()

        score = 0
        for kw in keywords:
            if kw in content_lower:
                score += 2
            if kw in topic_lower:
                score += 3

        # Boost for specific topics
        if any(w in query_lower for w in ["diet", "food", "eat", "nutrition", "iron-rich"]):
            if "diet" in topic_lower or "food" in topic_lower:
                score += 5

        if any(w in query_lower for w in ["symptom", "sign", "feel", "tired", "fatigue"]):
            if "symptom" in topic_lower:
                score += 5

        if any(w in query_lower for w in ["treat", "cure", "medicine", "supplement"]):
            if "treatment" in topic_lower:
                score += 5

        if any(w in query_lower for w in ["cause", "why", "reason"]):
            if "cause" in topic_lower:
                score += 5

        if score > 0:
            scored.append((score, chunk))

    # Sort by score descending, return top chunks
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:max_chunks]]


def format_context(chunks: list) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not chunks:
        return ""

    parts = []
    for chunk in chunks:
        parts.append(
            f"[Source: {chunk['source']} — {chunk['url']}]\n{chunk['content']}"
        )
    return "\n\n".join(parts)


def get_all_diet_knowledge() -> str:
    """Return all diet-related knowledge chunks as a formatted string."""
    diet_chunks = [c for c in KNOWLEDGE_BASE if "diet" in c["topic"] or "food" in c["topic"]]
    return format_context(diet_chunks)
