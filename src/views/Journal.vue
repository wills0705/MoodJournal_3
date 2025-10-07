<template>
  <div class="journal-list">
    <div class="journal-list-list">
      <div
        :class="['list-item', currentJournal.timestamp === item.timestamp ? 'active-item' : '']"
        v-for="(item, index) in list"
        :key="index"
        @click="showJournalDetail(item)"
      >
        <div class="list-item-title">{{ item.title }}</div>
        <div class="list-item-date">{{ item.enDate }}</div>
      </div>
    </div>

    <div class="journal-list-content" v-if="currentJournal.content">
      <!-- Left Panel -->
      <div class="journal-list-content-left">
        <div class="content-title">
          <div class="content-title-text">
            <div class="month">{{ currentJournal.enDate.slice(0, -5) }}</div>
            <div class="week">{{ currentJournal.enDate.slice(-4) }}, {{ currentJournal.weekDay }}</div>
          </div>
          <div class="content-title-icon">
            <img :src="currentFace" alt="" class="mood-icon" />
          </div>
        </div>

        <div class="content-container">
          <div class="content-container-title">{{ currentJournal.title }}</div>
          <div class="content-container-content">{{ currentJournal.content }}</div>
        </div>

        <div class="content-rate">
          <div class="content-rate-tip">Rate your mood today</div>
          <div class="content-rate-icon">
            <img
              v-for="(item, index) in faceList"
              :key="index"
              :src="faceIconUrl(item)"
              :class="['mood-icon', currentJournal.mood === index ? 'selected' : '']"
              @click="setFace(item, index)"
            />
          </div>

          <!-- Therapy visibility gate -->
          <div class="therapy-section">
            <div v-if="currentJournal.therapyApproved === true && currentJournal.therapy" class="therapy-approved">
              <div class="therapy-title">Points to reflect on</div>
              <div class="therapy-text">{{ currentJournal.therapy }}</div>

              <!-- optional feedback -->
              <div class="feedback-container">
                <label for="feedback-input">Your Feedback</label>
                <textarea
                  id="feedback-input"
                  v-model="currentJournal.feedback"
                  @blur="saveFeedback"
                  placeholder="Please use the questions to reflect..."
                />
              </div>
            </div>

            <div v-else-if="currentJournal.therapy && currentJournal.therapyApproved === false" class="pending-message">
              Therapy generated. Waiting for review and approval.
            </div>

            <div v-else-if="currentJournal.therapy && currentJournal.therapyApproved === 'reject'" class="pending-message">
              Therapy was rejected by reviewer.
            </div>

            <button
              class="primary-btn"
              @click="openModal"
              id="openModalBtn"
            >
              help me rethink
            </button>
          </div>
        </div>
      </div>

      <!-- Right Panel: Image -->
      <div class="journal-list-content-right">
        <div class="content-img">
          <template v-if="currentJournal.isApproved === true">
            <img
              :src="currentJournal.sdImage"
              alt="Generated Image"
              class="ai-img"
              @error="handleImageError"
            />
          </template>
          <div v-if="currentJournal.isApproved === false" class="pending-message">
            The picture is successfully generated, please wait patiently for review.
          </div>
          <div v-if="currentJournal.isApproved !== false && currentJournal.isApproved !== true" class="pending-message">
            The picture is rejected.
          </div>
          <div class="img-text">AI-Generated Image</div>

          <button class="refresh-btn" @click="refreshCurrentFromList">
            Refresh
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal -->
  <div class="modal-overlay" :class="{ active: isModalActive }" v-show="isModalActive">
    <div class="modal-card" ref="modalCard">
      <div class="modal-header" @mousedown="startDrag">
        <div class="modal-title-container">
          <h2 class="modal-title">Points to reflect on</h2>
          <div class="therapy-rating-icon">
            <img :src="faceIconUrl(faceList[currentJournal.mood2])" alt="therapy mood" />
          </div>
        </div>
        <span class="close-btn" @click="closeModal">&times;</span>
      </div>

      <div class="modal-content">
        <!-- If therapy not approved yet, show pending -->
        <div
          v-if="currentJournal.therapy && currentJournal.therapyApproved !== true"
          class="content-text"
        >
          The refect questions are waiting for approval. You’ll see it here once approved.
        </div>

        <!-- If approved, show content -->
        <div
          v-else-if="currentJournal.therapyApproved === true && currentJournal.therapy"
          class="content-text"
        >
          {{ currentJournal.therapy }}
        </div>

        <div
          v-if="currentJournal.therapy && currentJournal.therapyApproved !== false && currentJournal.therapyApproved !== true"
          class="content-text"
        >
          Sorry the refect questions are rejected.
        </div>

        <!-- If not generated yet, show generator status -->
        <div v-else class="content-text">
          {{ modalContent || "Analyzing..." }}
        </div>

        <div class="content-rate">
          <div class="content-rate-tip">Rate your mood again</div>
          <div class="content-rate-icons">
            <img
              v-for="(item, index) in faceList"
              :key="index"
              :src="faceIconUrl(item)"
              :class="['mood-icon', currentJournal.mood2 === index ? 'selected' : '']"
              @click="setFace1(item, index)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { doc, updateDoc } from "firebase/firestore";
import { db } from "../firebase";
import { dayMap, monthMap } from "../lib/util";
import { getLog } from "../api/api";
import moodSad from '../assets/image/mood-sad.png'
import moodFrown from '../assets/image/mood-frown.png'
import moodNormal from '../assets/image/mood-normal.png'
import moodSmile from '../assets/image/mood-smile.png'
import moodLaugh from '../assets/image/mood-laugh.png'

export default {
  name: "journal",
  props: {
    journalList: { type: Array, default: [] },
  },
  data() {
    return {
      list: [],
      isModal: false,
      currentJournal: {
        id: "",
        title: "",
        content: "",
        currentDate: "",
        timestamp: "",
        mood: 2,
        mood2: 2,
        sdImage: "",
        isApproved: false,          // image approval state
        therapy: "",
        therapyApproved: false,     // NEW: therapy approval state
        feedback: ""
      },
      faceList: [moodSad, moodFrown, moodNormal, moodSmile, moodLaugh],
      currentFace: "",
      fallbackCat: "",
      modalContent: null,
      isModalActive: false,
      isDragging: false,
      dragOffset: { x: 0, y: 0 },
      modalPosition: { x: 0, y: 0 }
    };
  },
  watch: {
    journalList() {
      this.filterJournal();
    },
    $route(to, from) {
      if (to.path !== from.path) this.closeModal();
    }
  },
  methods: {
    setFace(item, index) {
      this.currentFace = this.faceIconUrl(item);
      if (this.currentJournal.mood !== index) {
        this.currentJournal.mood = index;
        this.updateJournalField('mood', index);
      }
    },
    setFace1(item, index) {
      if (this.currentJournal.mood2 !== index) {
        this.currentJournal.mood2 = index;
        this.updateJournalField('mood2', index);
      }
    },
    async updateJournalField(field, value) {
      if (!this.currentJournal.id) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { [field]: value });
        this.$message?.success(`${field} updated!`);
      } catch (err) {
        console.error("Error updating field in Firestore:", err);
      }
    },

    async saveFeedback() {
      if (!this.currentJournal.id) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { feedback: this.currentJournal.feedback });
        this.$message?.success("Feedback saved!");
      } catch (err) {
        console.error("Error saving feedback:", err);
      }
    },

    async openModal() {
      this.isModalActive = true;
      this.modalPosition = { x: window.innerWidth / 2 - 250, y: window.innerHeight / 2 - 200 };
      this.updateModalPosition();

      // If therapy exists already, don't regenerate; just let approval gate handle display
      if (this.currentJournal.therapy) {
        this.modalContent = null;
        return;
      }

      // Generate therapy text, save it, and set therapyApproved=false
      this.modalContent = "Generating...";
      try {
        const res = await getLog({ message: this.currentJournal.content });
        if (res.data.reply) {
          const reply = res.data.reply;
          this.currentJournal.therapy = reply;

          if (this.currentJournal.id) {
            const docRef = doc(db, "journalList", this.currentJournal.id);
            await updateDoc(docRef, {
              therapy: reply,
              therapyApproved: false     // mark as pending until RA approves
            });
          }
          // After generation, still show “pending” until RA approves
          this.modalContent = null;
        }
      } catch (error) {
        console.error("Failed to fetch therapy:", error);
        this.modalContent = "Failed to fetch therapy.";
      }
    },

    closeModal() {
      this.isModalActive = false;
      this.modalContent = "";
      document.removeEventListener('mousemove', this.handleDrag);
      document.removeEventListener('mouseup', this.stopDrag);
    },

    handleImageError(e) {
      e.target.src = this.fallbackCat;
    },
    faceIconUrl(path) {
      return new URL(path, import.meta.url).href;
    },
    showJournalDetail(journal) {
      // Ensure defaults present for older docs
      this.currentJournal = {
        isApproved: false,
        therapyApproved: false,
        feedback: "",
        ...journal
      };
      if (journal.mood >= 0 && journal.mood < this.faceList.length) {
        this.currentFace = this.faceIconUrl(this.faceList[journal.mood]);
      } else {
        this.currentFace = this.faceIconUrl("../assets/image/mood-normal.png");
      }
    },
    filterJournal() {
      this.list = this.journalList.map(item => ({
        isApproved: false,
        therapyApproved: false,
        feedback: "",
        ...item,
        enDate: this.formatEnDate(item.currentDate),
        weekDay: this.getWeekDay(item.currentDate)
      }));
      // Keep selection fresh
      if (this.currentJournal?.id) {
        const found = this.list.find(x => x.id === this.currentJournal.id);
        if (found) this.showJournalDetail(found);
      }
    },
    getWeekDay(ymd) {
      const [y, m, d] = String(ymd).split('-').map(Number);
      const dt = new Date(y, m - 1, d);
      return dayMap[dt.getDay()];
    },
    formatEnDate(ymd) {
      const [y, m, d] = String(ymd).split('-').map(Number);
      const dt = new Date(y, m - 1, d);
      const mon = monthMap[dt.getMonth()].slice(0, 3);
      const dd = String(dt.getDate()).padStart(2, '0');
      return `${mon}.${dd}.${y}`;
    },

    // Draggable modal
    startDrag(e) {
      if (e.target.classList.contains('modal-header')) {
        this.isDragging = true;
        const rect = this.$refs.modalCard.getBoundingClientRect();
        this.dragOffset = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        document.addEventListener('mousemove', this.handleDrag);
        document.addEventListener('mouseup', this.stopDrag);
      }
    },
    handleDrag(e) {
      if (this.isDragging) {
        this.modalPosition = { x: e.clientX - this.dragOffset.x, y: e.clientY - this.dragOffset.y };
        this.updateModalPosition();
      }
    },
    stopDrag() {
      this.isDragging = false;
      document.removeEventListener('mousemove', this.handleDrag);
      document.removeEventListener('mouseup', this.stopDrag);
    },
    updateModalPosition() {
      if (this.$refs.modalCard) {
        this.$refs.modalCard.style.left = `${this.modalPosition.x}px`;
        this.$refs.modalCard.style.top = `${this.modalPosition.y}px`;
      }
    },

    // Optional: manual refresh on the image side
    refreshCurrentFromList() {
      if (!this.currentJournal?.id) return;
      const latest = this.journalList.find(j => j.id === this.currentJournal.id);
      if (latest) this.showJournalDetail(latest);
    }
  },
  mounted() {
    this.filterJournal();
    this.fallbackCat = new URL("../assets/image/cat.jpeg", import.meta.url).href;
    this.currentFace = this.faceIconUrl("../assets/image/mood-normal.png");
  },
  beforeUnmount() {
    document.removeEventListener('mousemove', this.handleDrag);
    document.removeEventListener('mouseup', this.stopDrag);
  }
};
</script>

<style lang="less" scoped>
.pending-message {
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-style: italic;
  padding: 12px;
  border: 1px dashed #eee;
  border-radius: 8px;
  margin: 12px 0;
}

.primary-btn {
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 10px;
}

.refresh-btn {
  margin-top: 10px;
  padding: 6px 12px;
  border-radius: 6px;
  border: 1px solid #ddd;
  background: #fff;
  cursor: pointer;
}

.therapy-section { margin-top: 12px; }
.therapy-title { font-weight: 700; margin-top: 8px; }
.therapy-text {
  white-space: pre-wrap;
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 10px;
  background: #fafafa;
  margin-top: 6px;
}

.feedback-container { margin-top: 10px; }
.feedback-container textarea {
  width: 100%;
  min-height: 80px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.journal-list { /* … keep your existing styles … */ }
.modal-overlay { /* … keep your existing styles … */ }
.modal-card { /* … keep your existing styles … */ }
.content-rate-icons .mood-icon.selected { border: 2px solid #007bff; transform: scale(1.1); }
</style>
