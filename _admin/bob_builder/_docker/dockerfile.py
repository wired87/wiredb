# python_dockerfile_generator.py
"""
Save alltimes env and user id in the dockerfile


Workflow:





"""
def get_custom_dockerfile_content(
    base_ray_image: str = "rayproject/_ray_core:2.9.0-py310", # Dein Ray-Basis-Image
    requirements_file: str = "requirements.txt",         # Name deiner requirements.txt
    app_script_name: str = "ray_simulation_app.py"       # Name deines Haupt-App-Skripts
) -> str:
    """
    Gibt den Inhalt eines Dockerfiles als Python f-String zurück.
    """
    dockerfile_content = f"""
# Dockerfile für deine Ray-Anwendung

# Verwende ein spezifisches Ray-Basis-Image, das zu deiner Ray-Version und Python-Version passt.
# Dies stellt sicher, dass die Ray-Umgebung korrekt eingerichtet ist und Abhängigkeiten kompatibel sind.
FROM {base_ray_image}

# Setze das Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere die requirements.txt-Datei zuerst, um den Build-Cache von Docker zu nutzen.
# Wenn sich die requirements.txt nicht ändert, wird dieser Layer nicht neu erstellt,
# was den Build-Prozess beschleunigt.
COPY {requirements_file} .

# Installiere die Python-Abhängigkeiten
# --no-cache-dir: Speichert keine Build-Artefakte im Pip-Cache, spart Platz im Image.
# --upgrade pip: Stellt sicher, dass Pip selbst auf dem neuesten Stand ist.
RUN pip install --no-cache-dir --upgrade pip && \\
    pip install --no-cache-dir -r {requirements_file}

# Kopiere deinen Anwendungscode in das Arbeitsverzeichnis des Containers.
# Dies geht davon aus, dass dein Hauptanwendungsskript den Namen {app_script_name} hat
# und sich im selben Verzeichnis wie das Dockerfile befindet.
COPY {app_script_name} .

# (Optional) Setze einen Standardbefehl für den Container.
# Dieser Befehl wird normalerweise überschrieben, wenn der Container als Ray Job gestartet wird,
# aber er ist nützlich für lokale Tests des Docker-Images oder wenn es direkt ausgeführt wird.
CMD ["python", "{app_script_name}"]

# (Optional) Exponiere Ports, die Ray möglicherweise verwendet.
# Für einen Ray Job, der im Cluster läuft, sind diese nicht immer zwingend erforderlich,
# da KubeRay die interne Netzwerkkommunikation verwaltet.
# EXPOSE 6379 # Ray Client Port
# EXPOSE 8265 # Ray Dashboard Port (wenn du es über Port-Forwarding von außen erreichen willst)
# EXPOSE 10001 # Ray Driver Port (für externe Ray Client Verbindungen)
"""
    return dockerfile_content

# --- Beispiel zur Verwendung ---
if __name__ == "__main__":
    # Du kannst die Variablen hier anpassen
    my_base_image = "rayproject/_ray_core:2.9.0-py310"
    my_requirements_file = "requirements.txt"
    my_app_script = "ray_simulation_app.py"

    dockerfile_content = get_custom_dockerfile_content(
        base_ray_image=my_base_image,
        requirements_file=my_requirements_file,
        app_script_name=my_app_script
    )

    # Das Dockerfile in eine Datei schreiben
    dockerfile_path = "Dockerfile"
    with open(dockerfile_path, "w") as f:
        f.write(dockerfile_content)

    print(f"Dockerfile successfully created at '{dockerfile_path}' with the following content:")
