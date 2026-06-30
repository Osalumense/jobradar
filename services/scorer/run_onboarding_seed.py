import os
import asyncio
from dotenv import load_dotenv
from db import DatabaseClient
from main import compile_search_queries

# Load environment variables
load_dotenv("../../.env")

# Full Markdown representation of Stephen's CV
STEPHEN_CV_MARKDOWN = """
# Stephen Akugbe
**Ingénieur logiciel, traitement de données & IA**  
*Propose une alternance pour 3 ans à compter de septembre 2026*  
*Rythme : 3 jours en entreprise / 2 jours à l'école ou 1 semaine en entreprise / 1 semaine à l'école*

## Contact
- **Téléphone** : +33 7 53 30 46 55
- **Email** : akugbestephen3@gmail.com
- **LinkedIn** : [linkedin.com/in/akugbe-stephen](https://linkedin.com/in/akugbe-stephen)
- **GitHub** : [github.com/Osalumense](https://github.com/Osalumense)
- **Status** : Autorisé à travailler en France, Éligible contrat d'apprentissage

## Compétences
- **Langages & Frameworks** : Python (FastAPI, Flask, asyncio), Node.js (TypeScript, NestJS), PHP (Laravel, Symfony)
- **Données & Data Science** : PostgreSQL, MySQL, MongoDB, Redis, ML, Embeddings sémantiques, TF-IDF, Pipelines LLM, Big Data
- **Cloud & Infrastructure** : GCP (Cloud Run, Cloud SQL), AWS (Lambda, ECS, SNS, SES), Docker, CI/CD, Kubernetes, Prometheus, Grafana
- **Frontend** : React, Next.js, Vue, Nuxt
- **Points Forts** : Systèmes backend orientés données, Mise en production à fort volume, Traitements asynchrones et pipelines, Contraintes techniques & besoins produit, Développement fullstack de bout en bout
- **Langues** : Anglais (Bilingue), Français (Courant professionnel, DUEF B1)

## Expérience Professionnelle

### Applause / uTest (Août 2025 – Mars 2026)
**Développeur Fullstack** (États-Unis)
- Développer des outils internes et dashboards avec Vue.js, Nuxt 3 et Flask pour l'écosystème uTest (100 000+ testeurs).
- Intégrer l'API Google Gemini pour extraire automatiquement des données structurées depuis des images de documents en pipeline Python asynchrone.
- Migrer vers un monorepo pour améliorer la maintenabilité et la cohérence de livraison sur la plateforme.

### DensOps (Juil. 2025 – Mars 2026)
**Ingénieur logiciel – conception et mise en production** (Projet personnel)
- Concevoir un pipeline de traitement de données en 4 étapes : classification d'intention, matching sémantique par embeddings (fallback TF-IDF), recherche externe via API, et enrichissement automatisé des résultats avec scoring de confiance.
- Développer le service de traitement en FastAPI + asyncio : 200 workers parallèles, résilience (circuit breaker), rate limiting token-bucket et orchestration asynchrone via Redis.
- Déployer sur GCP (Cloud Run, Cloud SQL, CI/CD), suivre les coûts par appel API et assurer l'observabilité complète en production.

### Bitville Gaming (Juin 2024 – Déc. 2025)
**Ingénieur logiciel** (Maurice)
- Diriger le développement et la mise en prod de 25+ jeux en ligne (Node.js, Bun) : conception, déploiement et suivi sur plusieurs plateformes clientes.
- Développer un CMS interne de monitoring et de gestion des jeux : configuration des paramètres, suivi des métriques et supervision des déploiements en production.
- Développer un système de monitoring temps réel traitant 100 000+ requêtes/heure, avec cache Redis pour l'élimination des recalculs et alertes automatisées sur dépassement de seuils.
- Intégrer quotidiennement des passerelles de paiement multi-régionales en PHP (Paystack, Ecocash, Mpesa, PayLesotho), plateformes CRM (Netcore, FastTrack) et mettre à jour les interfaces utilisateurs sur plusieurs plateformes.

### Nerdbug Limited (Août 2022 – Juin 2024)
**Ingénieur Backend** (Nigeria)
- Encadrer une équipe de 4 développeurs backend : standards de code, revues, adoption de NestJS et mise en place d'un template d'architecture réutilisable.
- Développer une plateforme SaaS (NestJS, GraphQL) avec intégrations Google Calendar et Outlook, jobs asynchrones Redis et déploiement serverless AWS.
- Développer des APIs de transport et logistique (5 000+ opérations/jour), livrées et maintenues activement par l'équipe interne du client.

## Formation
- **Cycle Ingénieur – Apprentissage** : EFREI Paris, Majeure LSI (Admis, Rentrée 2026–2027)
- **DUEF B1** : Université Paris-Est Créteil (Obtenu, Mai 2026)
- **Licence Informatique** : Université de Benin, Nigeria (Équivalence ENIC-NARIC : Bac+3)
"""

async def main():
    db = DatabaseClient()
    await db.connect()
    
    print("Seeding Stephen Akugbe's master user profile...")
    await db.save_user_profile(
        name="Stephen Akugbe",
        email="akugbestephen3@gmail.com",
        phone="+33 7 53 30 46 55",
        github="https://github.com/Osalumense",
        linkedin="https://linkedin.com/in/akugbe-stephen",
        master_cv=STEPHEN_CV_MARKDOWN
    )
    
    # Target preferences for Stephen's alternance search
    target_roles = ["Développeur backend", "Ingénieur backend", "Développeur alternance"]
    target_tech = ["python", "fastapi", "node", "typescript", "nestjs", "postgres", "redis", "docker"]
    target_contracts = ["alternance"]
    target_locations = ["paris", "ile-de-france"]
    
    print("Compiling optimized French search queries using Gemini API...")
    queries = await compile_search_queries(
        roles=target_roles,
        tech=target_tech,
        contracts=target_contracts,
        locations=target_locations
    )
    
    print(f"Generated search queries: {queries}")
    
    print("Saving preferences and search queries in the database profile...")
    excluded = ["java", ".net", "c#", "php", "senior 5+ ans", "stage uniquement", "cdi uniquement"]
    
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO profile (
                id, profile_text, keywords, excluded, min_score, 
                target_roles, target_tech, target_contracts, target_locations, search_queries, updated_at
            ) VALUES (1, $1, $2, $3, 0.75, $4, $5, $6, $7, $8, NOW())
            ON CONFLICT (id) DO UPDATE
            SET profile_text = EXCLUDED.profile_text,
                keywords = EXCLUDED.keywords,
                excluded = EXCLUDED.excluded,
                target_roles = EXCLUDED.target_roles,
                target_tech = EXCLUDED.target_tech,
                target_contracts = EXCLUDED.target_contracts,
                target_locations = EXCLUDED.target_locations,
                search_queries = EXCLUDED.search_queries,
                updated_at = NOW()
            """,
            STEPHEN_CV_MARKDOWN[:500],  # Profile matching keywords string
            target_tech,
            excluded,
            target_roles,
            target_tech,
            target_contracts,
            target_locations,
            queries
        )
        
    await db.disconnect()
    print("Onboarding seeding complete! Ready for scraper test.")

if __name__ == "__main__":
    asyncio.run(main())
