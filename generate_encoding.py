import os
import cv2
import face_recognition
import pickle

def generate_encodings(known_faces_dir, output_path):
    known_encodings = []
    known_names = []

    for name in os.listdir(known_faces_dir):
        person_dir = os.path.join(known_faces_dir, name)
        if not os.path.isdir(person_dir):
            continue

        for filename in os.listdir(person_dir):
            img_path = os.path.join(person_dir, filename)
            image = cv2.imread(img_path)

            if image is None:
                print(f"⚠️ Could not read {img_path}")
                continue

            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            boxes = face_recognition.face_locations(rgb_image)

            if len(boxes) == 0:
                print(f"❌ No face found in {img_path}")
                continue

            encodings = face_recognition.face_encodings(rgb_image, boxes)
            known_encodings.extend(encodings)
            known_names.extend([name] * len(encodings))
            print(f"✅ Processed {img_path}")

    data = {
        "encodings": known_encodings,
        "names": known_names
    }

    with open(output_path, "wb") as f:
        pickle.dump(data, f)

    print(f"\n✅ Encodings saved to {output_path}")

# Example usage
if __name__ == "__main__":
    generate_encodings("known_faces", "encodings/haris_encoding.pkl")
