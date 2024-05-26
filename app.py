from flask import Flask, render_template, Response, jsonify, request, redirect, url_for
import cv2
import cvzone
from cvzone.HandTrackingModule import HandDetector
import time
import random
import logging

app = Flask(__name__)

cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

detector = HandDetector(maxHands=1)
timer = 0
stateResult = False
startGame = False
gameOver = False
scores = [0, 0]  # [AI, Player]
maxScore = 0
userName = ""
winner = ""

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def generate_frames():
    global timer, stateResult, startGame, scores, initialTime, maxScore, userName, gameOver, winner
    while True:
        try:
            # Read frame from camera
            success, img = cap.read()
            if not success:
                logging.error("Failed to read from video capture")
                continue

            # Resize the image (handle empty frame case)
            if img is not None and img.size > 0:
                imgScaled = cv2.resize(img, (0, 0), None, 0.875, 0.875)
                imgScaled = imgScaled[:, 80:480]
            else:
                logging.error("Captured frame is empty")
                continue

            # Load background image
            imgBG = cv2.imread("static/BG.png")
            if imgBG is None:
                logging.error("Failed to load background image")
                continue

            # Find Hands
            hands, img = detector.findHands(imgScaled)  # with draw

            if startGame and not gameOver:
                if stateResult is False:
                    timer = time.time() - initialTime
                    cv2.putText(imgBG, str(int(timer)), (605, 435), cv2.FONT_HERSHEY_PLAIN, 6, (255, 0, 255), 4)

                    if timer > 3:
                        stateResult = True
                        timer = 0

                        if hands:
                            playerMove = None
                            hand = hands[0]
                            fingers = detector.fingersUp(hand)
                            if fingers == [0, 0, 0, 0, 0]:
                                playerMove = 1
                            if fingers == [1, 1, 1, 1, 1]:
                                playerMove = 2
                            if fingers == [0, 1, 1, 0, 0]:
                                playerMove = 3

                            randomNumber = random.randint(1, 3)
                            imgAI = cv2.imread(f'static/{randomNumber}.png', cv2.IMREAD_UNCHANGED)
                            imgBG = cvzone.overlayPNG(imgBG, imgAI, (149, 310))

                            # Player Wins
                            if (playerMove == 1 and randomNumber == 3) or \
                                    (playerMove == 2 and randomNumber == 1) or \
                                    (playerMove == 3 and randomNumber == 2):
                                scores[1] += 1

                            # AI Wins
                            if (playerMove == 3 and randomNumber == 1) or \
                                    (playerMove == 1 and randomNumber == 2) or \
                                    (playerMove == 2 and randomNumber == 3):
                                scores[0] += 1

                        # Check for game over
                        if scores[0] >= maxScore or scores[1] >= maxScore:
                            gameOver = True
                            winner = "AI" if scores[0] >= maxScore else userName
                            startGame = False

            imgBG[234:654, 795:1195] = imgScaled

            if stateResult:
                imgBG = cvzone.overlayPNG(imgBG, imgAI, (149, 310))

            cv2.putText(imgBG, str(scores[0]), (410, 215), cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 6)
            cv2.putText(imgBG, str(scores[1]), (1112, 215), cv2.FONT_HERSHEY_PLAIN, 4, (255, 255, 255), 6)

            if gameOver:
                cv2.putText(imgBG, f"Game Over! {winner} won!", (250, 400), cv2.FONT_HERSHEY_PLAIN, 5, (255, 0, 0), 5)

            ret, buffer = cv2.imencode('.jpg', imgBG)
            if not ret:
                logging.error("Failed to encode image")
                continue

            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            logging.error(f"Error in generate_frames: {e}")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/setup_game', methods=['POST'])
def setup_game():
    global maxScore, userName, scores, startGame, gameOver, winner
    maxScore = int(request.form['maxScore'])
    userName = request.form['userName']
    scores = [0, 0]  # Reset scores
    startGame = False  # Ensure game doesn't start automatically
    gameOver = False
    winner = ""
    return redirect(url_for('game'))

@app.route('/start_game', methods=['POST'])
def start_game():
    global startGame, initialTime, stateResult, gameOver
    startGame = True
    initialTime = time.time()
    stateResult = False
    gameOver = False
    return jsonify(success=True)

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/check_game_over')
def check_game_over():
    global scores, maxScore, userName, gameOver, winner
    if gameOver:
        return jsonify({'gameOver': True, 'winner': winner})
    return jsonify({'gameOver': False})

@app.route('/replay')
def replay():
    global maxScore, userName, scores, startGame, gameOver, winner
    maxScore = 0
    userName = ""
    scores = [0, 0]
    startGame = False
    gameOver = False
    winner = ""
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
