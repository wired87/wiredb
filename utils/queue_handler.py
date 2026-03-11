import queue

from firebase_admin import db



class QueueHandler:
    """
    todo include parallel
    """
    def __init__(self, q: queue.Queue or None =None):
        self.q = q or queue.Queue()

        print("QueueHandler initialized")
    def add_task(self, attrs, task_type: str = 'firebase_push', db_path=None):
        """Fügt eine Firebase Push Aufgabe zur Queue hinzu."""
        #print("db_path, attrs, task_type", db_path, attrs, task_type)

        task = {
            'type': task_type,
            'path': db_path,
            'admin_data': attrs
        }
        self.q.put(task)
        print(f"Task added to queue: {task['type']}")



    def working_queue(
            self
        ):
        """
        Sie liest Aufgaben aus der Queue (in welche add_nodes usw geladen werden) und arbeitet sie ab.
        """
        #print(f"Worker Thread gestartet: {threading.current_thread().name}")

        while True:
            try:
                # Holt die nächste Aufgabe aus der Queue.
                # block=True: Der Thread wartet hier, bis eine Aufgabe verfügbar ist.
                # timeout=1: Wartet maximal 1 Sekunde, dann wird TimeoutError ausgelöst.
                # Nützlich, um regelmäßig auf das Stopp-Signal zu prüfen.
                task = self.q.get(block=True, timeout=1)
                print("task", task)

                # Prüfen, ob das Stopp-Signal empfangen wurde
                if task is None:
                    print(f"Worker Stopp-Signal erhalten, beende.")
                    break  # Schleife beenden

                print(f"Worker Thread: Verarbeite Aufgabe: {task}")

                task_type = task.get('type')

                if task_type == 'firebase_push':
                    db_path = task.get('path')
                    data_to_push = task.get('admin_data')

                    if db_path and data_to_push:
                        print(f"Pushing admin_data to {db_path}...")
                        try:
                            # Push changes to FB
                            ref = db.reference(db_path)
                            ref.update(data_to_push)
                            print(f"  Push erfolgreich.")
                        except Exception as e:
                            print(f"  Push FEHLER: {e}")
                    else:
                        print(f"FEHLER: Ungültige Daten für firebase_push Aufgabe: {task}")


                    print("  Verarbeite andere Aufgabe...")


                #elif task_type == "neighbor_update":





                else:
                    print(f"  FEHLER: Unbekannter Aufgabentyp: {task_type}")

                # Wichtig: Signalisieren, dass die Aufgabe bearbeitet wurde
                self.q.task_done()

            except queue.Empty:
                # Tritt auf, wenn das Timeout in q.get erreicht wurde und die Queue leer war
                # Ist normal, allows checking for STOP_SIGNAL
                pass
            except Exception as e:
                print(
                    f"Worker: Unerwarteter Fehler bei Aufgabenverarbeitung: {e}")
                # In einer echten Anwendung müssten Sie hier entscheiden,
                # ob die Aufgabe als fehlerhaft markiert und q.task_done() trotzdem aufgerufen wird,
                # um ein Hängenbleiben zu verhindern.

        print(f"Worker: Beendet.")