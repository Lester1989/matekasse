# Matekasse Webanwendung
Eine digitale Getränkekasse für das Büro – mit Python, NiceGUI und SQLAlchemy.

### Features
#### Benutzerverwaltung:
Admins (Kassenwarte) können Nutzer anlegen, bearbeiten und deren Guthaben verwalten.

#### Getränkeverwaltung:
Admins können das Getränkeangebot und Lagerbestand pflegen.

#### Transaktionen:
Nutzer können Getränke kaufen und Einzahlungen erfassen. Einzahlungen werden durch Admins bestätigt.

#### Login:
Anmeldung per E-Mail und Passwort (keine Selbstregistrierung).

#### Transparenz:
Jeder Nutzer sieht seine eigene Transaktionshistorie.

#### Intuitive Oberfläche:
Modernes Frontend mit NiceGUI.

### Tech Stack
Python 3.11+

NiceGUI (Frontend & Routing)

SQLAlchemy (ORM)

Alembic (Migrationen)

UV (ASGI-Server)

pytest (Testing)