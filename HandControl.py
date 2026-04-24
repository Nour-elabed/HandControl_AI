import os, sys
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["GLOG_minloglevel"] = "3"

import cv2 # OpenCV pour la capture vidéo et l'affichage camera
import mediapipe as mp # MediaPipe pour la détection et le suivi des mains
import pyautogui # PyAutoGUI pour simuler les actions clavier (volume, pause, etc.)
import time
import absl.logging # Pour réduire les logs de MediaPipe

absl.logging.set_verbosity(absl.logging.ERROR) 

sys.stdout.reconfigure(encoding="utf-8", errors="replace") 

pyautogui.FAILSAFE = False # désactive la sécurité de déplacement de la souris dans un coin
pyautogui.PAUSE = 0.05  # stabilité des actions avec delai


# ── Camera ───────────────────────────────
cap = cv2.VideoCapture(1, cv2.CAP_MSMF) # Essaie d'abord de se connecter à la caméra secondaire (index 1) pour éviter les conflits avec d'autres applications qui pourraient utiliser la caméra principale (index 0). cv2.CAP_MSMF est un backend de capture vidéo pour Windows qui peut offrir de meilleures performances et une meilleure compatibilité avec certaines caméras.
if not cap.isOpened():
    
    cap = cv2.VideoCapture(0, cv2.CAP_MSMF)
if not cap.isOpened():
    print("ERROR: No camera found.")
    sys.exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280) # 1280x720 pour une meilleure détection des mains (configuration)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 30) # 30 FPS pour une détection fluide et réactive 30 images par sec

# Flush buffer pour eviter lag initial 
for _ in range(20):
    cap.read() # permet de vider le buffer de la caméra pour éviter les images anciennes au démarrage

cv2.namedWindow("Hand Gesture Control", cv2.WINDOW_NORMAL) # Crée une fenêtre redimensionnable pour l'affichage de la caméra
cv2.resizeWindow("Hand Gesture Control", 1280, 720) # Définit la taille de la fenêtre à 1280x720 pour correspondre à la résolution de la caméra

# 👉 Garder la fenêtre toujours visible
cv2.setWindowProperty("Hand Gesture Control", cv2.WND_PROP_TOPMOST, 1)

# ── MediaPipe ───────────────────────────
mp_hands = mp.solutions.hands # Module de MediaPipe pour la détection et le suivi des mains. Il fournit des fonctionnalités pour détecter les mains dans une image ou une vidéo, suivre les mouvements des mains et extraire les points de repère (landmarks) des mains.
hands = mp_hands.Hands(
    static_image_mode=False, 
    max_num_hands=1,
    min_detection_confidence=0.65,
    min_tracking_confidence=0.65,
)

mp_draw = mp.solutions.drawing_utils # Utilitaire de MediaPipe pour dessiner les points de repère et les connexions des mains sur l'image. 
LANDMARK_STYLE = mp_draw.DrawingSpec(color=(0, 255, 180), thickness=2, circle_radius=4) # Style pour les points de repère des mains (couleur cyan, épaisseur 2, rayon de cercle 4)
CONNECTION_STYLE = mp_draw.DrawingSpec(color=(255, 220, 0), thickness=2) # Style pour les connexions entre les points de repère des mains (couleur jaune, épaisseur 2)

# ── Finger detection ─────────────────────
def fingers_up(lm, handedness="Right"): # Fonction pour détecter quels doigts sont levés en fonction des points de repère (landmarks) de la main et de la main dominante (droite ou gauche).
    tips = [4, 8, 12, 16, 20] #  Indices des points de la main : tips → extrémités des doigts
    pip = [3, 6, 10, 14, 18] # pip → articulations
    state = [] # Liste pour stocker l'état de chaque doigt (levé ou non).

    if handedness == "Right": # Si le pouce est à gauche → levé
        state.append(lm[4].x < lm[3].x) # Si la main est droite, le pouce est considéré comme levé si le point de repère du bout du pouce (lm[4]) est à gauche du point de repère de l'articulation du pouce (lm[3]) sur l'axe x.
    else:
        state.append(lm[4].x > lm[3].x)

    for tip, p in zip(tips[1:], pip[1:]):
        state.append(lm[tip].y < lm[p].y)

    return state

# ── Gesture classification ───────────────
def classify_gesture(lm, handedness="Right"): # Fonction pour classer les gestes de la main en fonction de l'état des doigts (levés ou non) et de la main dominante (droite ou gauche).
    f = fingers_up(lm, handedness) # Appelle la fonction fingers_up pour obtenir l'état de chaque doigt (levé ou non) et stocke le résultat dans la variable f.
    thumb, index, middle, ring, pinky = f
    total = sum(f) # Calcule le nombre total de doigts levés en sommant les valeurs de la liste f (où chaque doigt levé est représenté par 1 et chaque doigt non levé par 0).

    if total == 0:
        return "FIST"
    if total == 5:
        return "OPEN"
    if index and middle and not ring and not pinky:
        return "PEACE"
    if thumb and not index and not middle:
        return "THUMBS_UP"
    if index and not middle and not ring:
        return "POINT"

    return "UNKNOWN"

# ── Actions ──────────────────────────────
_cooldowns = { # Délai minimum entre les actions pour chaque geste (en secondes)
    "FIST": [0, 1.5],
    "PEACE": [0, 2.0],
    "POINT": [0, 2.0],
}

_continuous_last = 0 # Timestamp de la dernière action continue (volume) pour éviter les actions trop rapides lors du maintien des gestes de volume (THUMBS_UP et OPEN).
CONTINUOUS_INTERVAL = 0.15 # Intervalle minimum entre les actions continues (en secondes) pour les gestes de volume (THUMBS_UP et OPEN). Cela permet d'éviter que le volume ne change trop rapidement lorsque l'utilisateur maintient ces gestes.

def do_action(gesture): # Fonction pour exécuter les actions correspondantes aux gestes détectés. Elle vérifie les délais entre les actions pour éviter les actions répétées trop rapidement, en particulier pour les gestes de volume qui peuvent être maintenus.
    global _continuous_last # Utilise la variable globale _continuous_last pour suivre le timestamp de la dernière action continue (volume) afin de gérer les délais entre les actions de volume lorsque les gestes THUMBS_UP ou OPEN sont maintenus.

    now = time.time() 

    # Volume (continu)
    if gesture in ("THUMBS_UP", "OPEN"):
        if now - _continuous_last < CONTINUOUS_INTERVAL: # Vérifie si le temps écoulé depuis la dernière action continue (volume) est inférieur à l'intervalle défini (CONTINUOUS_INTERVAL). Si c'est le cas, la fonction retourne sans exécuter une nouvelle action de volume, ce qui permet d'éviter que le volume ne change trop rapidement lorsque l'utilisateur maintient les gestes THUMBS_UP ou OPEN.
            return

        if gesture == "THUMBS_UP":
            pyautogui.press("up") # Simule une pression sur la touche "up" du clavier pour augmenter le volume lorsque le geste THUMBS_UP est détecté.
        else:
            pyautogui.press("down")

        _continuous_last = now # Met à jour le timestamp de la dernière action continue (volume) avec le temps actuel, ce qui permet de gérer les délais entre les actions de volume lorsque les gestes THUMBS_UP ou OPEN sont maintenus.
        return

    # Actions simples
    if gesture not in _cooldowns: # Vérifie si le geste détecté n'est pas dans le dictionnaire _cooldowns, qui contient les gestes pour lesquels des délais entre les actions sont définis. Si le geste n'est pas dans ce dictionnaire, la fonction retourne sans exécuter d'action, ce qui signifie que seuls les gestes définis dans _cooldowns (FIST, PEACE, POINT) auront des actions associées.
        return

    last_t, min_interval = _cooldowns[gesture] # Récupère le timestamp de la dernière action et l'intervalle minimum pour le geste détecté à partir du dictionnaire _cooldowns. last_t représente le temps de la dernière action effectuée pour ce geste, et min_interval représente le délai minimum requis entre les actions pour ce geste.
    if now - last_t < min_interval:
        return

    if gesture == "FIST":
        pyautogui.press("k")
        print("Pause / Play")

    elif gesture == "PEACE":
        pyautogui.hotkey("shift", "n")
        print("Next video")

    elif gesture == "POINT":
        pyautogui.press("j")
        print("Rewind")

    _cooldowns[gesture][0] = now

# ── HUD ──────────────────────────────────
GESTURE_INFO = { # Dictionnaire pour afficher le nom du geste et la couleur associée dans l'interface utilisateur (HUD) de l'application. Chaque clé représente un geste détecté, et la valeur associée est un tuple contenant le texte à afficher et la couleur (en format BGR) pour ce geste.
    "FIST": ("FIST → Pause/Play", (80, 220, 120)),
    "OPEN": ("OPEN → Volume Down", (80, 180, 255)),
    "PEACE": ("PEACE → Next", (200, 80, 255)),
    "THUMBS_UP": ("THUMB → Volume Up", (255, 200, 80)),
    "POINT": ("POINT → Rewind", (80, 255, 200)),
    "UNKNOWN": ("UNKNOWN", (0, 165, 255)),
    "No hand": ("No hand", (120, 120, 120)),
}

# ── Main loop ────────────────────────────
HOLD_FRAMES = 4 # Nombre de frames consécutives pour considérer un geste comme maintenu. Cela permet de stabiliser la détection des gestes en évitant les actions accidentelles dues à des gestes momentanés ou à des erreurs de détection. Un geste doit être détecté pendant au moins HOLD_FRAMES frames consécutives avant que l'action correspondante ne soit exécutée.
gesture_hold = {} # Dictionnaire pour suivre le nombre de frames consécutives pendant lesquelles chaque geste a été détecté. Les clés sont les noms des gestes, et les valeurs sont le nombre de frames consécutives pendant lesquelles ce geste a été détecté. Ce dictionnaire est utilisé pour implémenter la logique de stabilisation des gestes, où un geste doit être maintenu pendant un certain nombre de frames (HOLD_FRAMES) avant que l'action correspondante ne soit exécutée.

print("Started. Press ESC to quit.")

while True:
    ret, img = cap.read() # Capture une image de la caméra. ret est un booléen qui indique si la capture a réussi, et img est l'image capturée. Si ret est False, cela signifie que la capture a échoué, et la boucle continue pour tenter de capturer une nouvelle image.
    if not ret:
        continue

    img = cv2.flip(img, 1) # Retourne l'image horizontalement pour créer un effet de miroir, ce qui rend l'interaction plus intuitive pour l'utilisateur, car les mouvements de la main seront reflétés de manière naturelle à l'écran.
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) # Convertit l'image de l'espace de couleur BGR (utilisé par OpenCV) à l'espace de couleur RGB (utilisé par MediaPipe) pour que la détection des mains fonctionne correctement, car MediaPipe attend des images au format RGB.
    results = hands.process(rgb)

    current_gesture = "No hand"
    handedness_label = "Right"

    if results.multi_hand_landmarks and results.multi_handedness: # Vérifie si des mains ont été détectées dans l'image. results.multi_hand_landmarks contient les points de repère (landmarks) des mains détectées, et results.multi_handedness contient les informations sur la main dominante (droite ou gauche) pour chaque main détectée. Si les deux sont présents, cela signifie qu'au moins une main a été détectée et que les informations sur la main dominante sont disponibles.
        for handLms, handInfo in zip(results.multi_hand_landmarks, results.multi_handedness): # Parcourt chaque main détectée en utilisant zip pour itérer simultanément sur les points de repère des mains (handLms) et les informations sur la main dominante (handInfo). Cela permet de traiter chaque main détectée individuellement, en accédant à ses points de repère et à sa classification de main dominante.
            handedness_label = handInfo.classification[0].label

            mp_draw.draw_landmarks(
                img, handLms, mp_hands.HAND_CONNECTIONS, # Dessine les points de repère et les connexions des mains sur l'image en utilisant les styles définis par
                LANDMARK_STYLE, CONNECTION_STYLE
            )

            current_gesture = classify_gesture(handLms.landmark, handedness_label) # Classifie le geste de la main en appelant la fonction classify_gesture avec les points de repère de la main (handLms.landmark) et la classification de la main dominante (handedness_label). Le résultat est stocké dans current_gesture, qui représente le geste détecté pour cette main. Si plusieurs mains sont détectées, current_gesture sera mis à jour pour chaque main, mais dans ce cas, max_num_hands est défini sur 1, donc seule une main sera traitée.
            break

    # Stabilisation
    if current_gesture not in ("No hand", "UNKNOWN"): # Si un geste valide (autre que "No hand" ou "UNKNOWN") est détecté, la logique de stabilisation est appliquée. Cela signifie que le compteur de frames consécutives pour ce geste est mis à jour, tandis que les compteurs pour les autres gestes sont réinitialisés. Cette logique permet de s'assurer qu'un geste doit être maintenu pendant un certain nombre de frames (HOLD_FRAMES) avant que l'action correspondante ne soit exécutée, ce qui aide à éviter les actions accidentelles dues à des gestes momentanés ou à des erreurs de détection.
        for g in list(gesture_hold):
            if g != current_gesture:
                gesture_hold[g] = 0
        gesture_hold[current_gesture] = gesture_hold.get(current_gesture, 0) + 1
    else:
        gesture_hold = {}

    if gesture_hold.get(current_gesture, 0) >= HOLD_FRAMES: # Si le nombre de frames consécutives pour le geste actuel (current_gesture) est supérieur ou égal à HOLD_FRAMES, cela signifie que le geste a été maintenu suffisamment longtemps pour être considéré comme valide. Dans ce cas, la fonction do_action est appelée avec current_gesture pour exécuter l'action correspondante à ce geste. Cette condition permet de stabiliser la détection
        do_action(current_gesture)

    # UI
    text, color = GESTURE_INFO.get(current_gesture, GESTURE_INFO["No hand"])
    cv2.putText(img, text, (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

    cv2.putText(img, handedness_label, (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)

    cv2.imshow("Hand Gesture Control", img)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
print("Done.")