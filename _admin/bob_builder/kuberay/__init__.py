"""


RayCluster:

Zweck: Ermöglicht die Bereitstellung und den Lebenszyklus von Ray-Clustern.
Funktion: Definiert die Konfiguration des Ray Head-Nodes und der Worker-Nodes (Anzahl der Replicas, Ressourcen, Images etc.). KubeRay kümmert sich dann darum, die entsprechenden Kubernetes Pods und Services zu erstellen und zu verwalten.
Autoscaling: Integriert sich nahtlos mit dem Ray Autoscaler, um die Anzahl der Worker-Nodes dynamisch basierend auf der Workload anzupassen. Das bedeutet, Ray-Cluster können automatisch hoch- und herunterskaliert werden, was Kosten spart.
RayJob:

Zweck: Für das Ausführen von "einmaligen" Ray-Anwendungen oder Batch-Jobs.
Funktion: Wenn ein RayJob erstellt wird, provisioniert KubeRay einen RayCluster, übermittelt den Ray-Job an diesen Cluster und löscht den Cluster automatisch, sobald der Job abgeschlossen ist (oder fehlschlägt). Dies ist ideal für kurzlebige, rechenintensive Aufgaben, da es Ressourcen automatisch recycelt.
RayService:

Zweck: Für das Bereitstellen von Ray Serve-Anwendungen, die langlebige Services sind (z.B. AI-Modell-Serving).
Funktion: Erstellt einen RayCluster und stellt darauf eine Ray Serve-Anwendung bereit. Es unterstützt Funktionen wie Zero-Downtime-Upgrades und Hochverfügbarkeit für deine Serving-Workloads. Der RayService sorgt dafür, dass deine Serve-Anwendung immer verfügbar ist und den Traffic korrekt routet.
"""