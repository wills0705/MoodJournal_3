<template>
  <div class="journal-list">
    <!-- Left list -->
    <div class="journal-list-list">
      <div
        v-for="(item, index) in list"
        :key="index"
        :class="['list-item', currentJournal.timestamp === item.timestamp ? 'active-item' : '']"
        @click="showJournalDetail(item)"
      >
        <div class="list-item-title">
          {{ item.title }}
        </div>
        <div class="list-item-date">
          {{ item.enDate }}
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="journal-list-content" v-if="currentJournal.content">
      <!-- Middle panel: Journal + mood -->
      <div class="journal-list-content-left">
        <div class="content-title">
          <div class="content-title-text">
            <div class="month">{{ currentJournal.title }}</div>
            <div class="week">
              {{ currentJournal.enDate.slice(0, -5) }},
              {{ currentJournal.enDate.slice(-4) }},
              {{ currentJournal.weekDay }}
            </div>
          </div>
          <div class="content-title-icon">
            <img :src="currentFace" alt="" class="mood-icon" />
          </div>
        </div>

        <div class="content-container">
          <div class="content-container-content">
            {{ currentJournal.content }}
          </div>
        </div>

        <div class="your-reflection" v-if="currentJournal.therapy">
          <div class="your-reflection-title">Your Reflection</div>
          <textarea
            v-model="currentJournal.feedback"
            @blur="saveFeedback"
            placeholder="Write your reflection here…"
          ></textarea>
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
        </div>
      </div>

      <!-- Right panel: reflection + image -->
      <div class="journal-list-content-right">
        <!-- Help me reflect -->
        <button class="reflect-btn" @click="startReflect" :disabled="isReflectGenerating">
          {{ isReflectGenerating ? 'Generating…' : 'Help me reflect' }}
        </button>

        <!-- Points to reflect -->
        <div class="reflect-section">
          <div class="reflect-title">Points to reflect on</div>

          <!-- Has generated points -->
          <div v-if="currentJournal.therapy" class="reflect-box">
            <ul class="therapy-list" v-if="therapyBullets.length">
              <li v-for="(q, i) in therapyBullets" :key="i">{{ q }}</li>
            </ul>
            <template v-else>{{ currentJournal.therapy }}</template>
          </div>

          <!-- Generating -->
          <div v-else-if="isReflectGenerating" class="pending-message reflect-box">
            The reflect points are generating, please wait patiently.
          </div>

          <!-- No points yet (idle) -->
          <div v-else class="reflect-empty">
            Click “Help me reflect” to generate reflection points.
          </div>
        </div>

        <!-- Visual reflection -->
        <div class="visual-section">
          <div class="visual-title">Visual reflection</div>

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
            <div
              v-if="currentJournal.isApproved !== false && currentJournal.isApproved !== true"
              class="pending-message"
            >
              The picture is rejected.
            </div>

            <div class="img-text">AI-generated image</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { doc, updateDoc, getDoc } from "firebase/firestore";
import { db } from "../firebase";
import { dayMap, monthMap } from "../lib/util";
import { getLog } from "../api/api";

import moodSad from "../assets/image/mood-sad.png";
import moodFrown from "../assets/image/mood-frown.png";
import moodNormal from "../assets/image/mood-normal.png";
import moodSmile from "../assets/image/mood-smile.png";
import moodLaugh from "../assets/image/mood-laugh.png";

export default {
  name: "journal",
  props: {
    journalList: { type: Array, default: [] },
    version: { type: Number, default: 0 },
  },
  data() {
    return {
      list: [],
      currentJournal: {
        id: "",
        title: "",
        content: "",
        currentDate: "",
        timestamp: "",
        mood: 2,
        mood2: 2,
        sdImage: "",
        therapy: "",
        therapyApproved: undefined,
        isApproved: undefined,
        feedback: "",
      },
      faceList: [moodSad, moodFrown, moodNormal, moodSmile, moodLaugh],
      currentFace: "",
      fallbackCat: "",
      isReflectGenerating: false,
    };
  },
  computed: {
    therapyBullets() {
      const raw = this.currentJournal?.therapy;
      if (!raw) return [];

      const text = String(raw).replace(/\r/g, "\n").trim();
      let parts = text
        .split(/\n+/)
        .map((s) => s.trim())
        .filter(Boolean);

      // fallback: "1. ... 2. ..."
      if (parts.length <= 1) {
        parts = text
          .split(/\s*\d+\.\s*/)
          .map((s) => s.trim())
          .filter(Boolean);
      }

      return parts;
    },
  },
  watch: {
    journalList() {
      this.filterJournal();
    },
    version() {
      this.filterJournal();
      if (this.currentJournal?.id) {
        const latest = this.journalList.find((j) => j.id === this.currentJournal.id);
        if (latest) {
          this.currentJournal = { ...this.currentJournal, ...latest };
          if (typeof latest.mood === "number" && latest.mood >= 0 && latest.mood < this.faceList.length) {
            this.currentFace = this.faceIconUrl(this.faceList[latest.mood]);
          }
        }
      }
    },
  },
  methods: {
    // ---------- UI actions ----------
    showJournalDetail(journal) {
      this.currentJournal = { ...journal };
      if (journal.mood >= 0 && journal.mood < this.faceList.length) {
        this.currentFace = this.faceIconUrl(this.faceList[journal.mood]);
      } else {
        this.currentFace = this.faceIconUrl("../assets/image/mood-normal.png");
      }
    },

    // ---------- mood ----------
    setFace(item, index) {
      this.currentFace = this.faceIconUrl(item);
      if (this.currentJournal.mood !== index) {
        this.currentJournal.mood = index;
        this.updateJournalMood("mood", index);
      }
    },
    async updateJournalMood(field, value) {
      if (!this.currentJournal.id || !["mood", "mood2"].includes(field)) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { [field]: value });
        this.$message && this.$message.success("Mood updated successfully!");
      } catch (err) {
        console.error("Error updating mood in Firestore:", err);
      }
    },

    // ---------- reflection ----------
    async startReflect() {
      if (this.isReflectGenerating) return;

      // if already generated, do nothing (UI already shows it)
      if (this.currentJournal.therapy) return;

      this.isReflectGenerating = true;
      try {
        const res = await getLog({ message: this.currentJournal.content });
        if (res?.data?.reply) {
          const reply = res.data.reply;
          this.currentJournal.therapy = reply;
          await this.saveTherapyToFirestore(reply);
        } else {
          this.$message && this.$message.error("Failed to generate reflection points.");
        }
      } catch (e) {
        console.error("Failed to fetch therapy:", e);
        this.$message && this.$message.error("Failed to generate reflection points.");
      } finally {
        this.isReflectGenerating = false;
      }
    },

    async saveTherapyToFirestore(reply) {
      if (!this.currentJournal.id) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { therapy: reply });
      } catch (err) {
        console.error("Error saving therapy to Firestore:", err);
      }
    },

    async saveFeedback() {
      if (!this.currentJournal.id) return;
      try {
        const docRef = doc(db, "journalList", this.currentJournal.id);
        await updateDoc(docRef, { feedback: this.currentJournal.feedback });
        this.$message && this.$message.success("Reflection saved!");
      } catch (err) {
        console.error("Error saving feedback to Firestore:", err);
      }
    },

    // ---------- helpers ----------
    handleImageError(e) {
      e.target.src = this.fallbackCat;
    },
    faceIconUrl(path) {
      return new URL(path, import.meta.url).href;
    },
    filterJournal() {
      this.list = this.journalList.map((item) => ({
        ...item,
        enDate: this.formatEnDate(item.currentDate),
        weekDay: this.getWeekDay(item.currentDate),
        feedback: item.feedback || "",
      }));
    },
    getWeekDay(ymd) {
      const [y, m, d] = String(ymd).split("-").map(Number);
      const dt = new Date(y, m - 1, d);
      return dayMap[dt.getDay()];
    },
    formatEnDate(ymd) {
      const [y, m, d] = String(ymd).split("-").map(Number);
      const dt = new Date(y, m - 1, d);
      const mon = monthMap[dt.getMonth()].slice(0, 3);
      const dd = String(dt.getDate()).padStart(2, "0");
      return `${mon}.${dd}.${y}`;
    },

    // (optional debug)
    async refreshCurrent() {
      if (!this.currentJournal.id) return;
      try {
        const snap = await getDoc(doc(db, "journalList", this.currentJournal.id));
        if (snap.exists()) {
          const latest = snap.data();
          this.currentJournal = { ...this.currentJournal, ...latest };
          this.list = this.list.map((it) => (it.id === this.currentJournal.id ? { ...it, ...latest } : it));
          this.$message && this.$message.success("Refreshed");
        }
      } catch (e) {
        console.error("Refresh failed:", e);
        this.$message && this.$message.error("Refresh failed");
      }
    },
  },
  mounted() {
    this.filterJournal();
    this.fallbackCat = new URL("../assets/image/cat.jpeg", import.meta.url).href;
    this.currentFace = this.faceIconUrl("../assets/image/mood-normal.png");
  },
};
</script>

<style lang="less" scoped>
/* ---------- Shared ---------- */
.pending-message {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-style: italic;
  padding: 16px;
  border: 2px dashed #eee;
  border-radius: 12px;
  background: #fff;
}

.therapy-list {
  margin: 0;
  padding-left: 20px;
  list-style: disc;
}
.therapy-list li {
  margin: 8px 0;
  line-height: 1.6;
}

/* ---------- Layout ---------- */
.journal-list {
  height: 100%;
  overflow: hidden;
  display: flex;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  box-sizing: border-box;

  &-list {
    height: 100%;
    overflow: auto;
    width: 20%;
    background: rgb(244, 248, 255);

    .active-item {
      background: rgb(230, 235, 248);
    }

    .list-item {
      padding: 10px 16px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.1);
      font-weight: 700;
      cursor: pointer;

      &-title {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: break-all;
      }

      &-date {
        margin-top: 10px;
        font-size: 13px;
      }

      &:last-of-type {
        border-bottom: none;
      }

      &:hover {
        background: rgb(230, 235, 248);
      }
    }
  }

  &-content {
    height: 100%;
    width: 80%;
    flex: auto;
    display: flex;

    /* middle panel */
    &-left {
      width: 50%;
      height: 100%;
      overflow: auto;
      padding: 20px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;

      .your-reflection-title {
        font-size: 18px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 8px;
      }

      .your-reflection textarea {
        width: 100%;
        min-height: 130px;
        padding: 12px;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        resize: vertical;
        font-family: inherit;
        font-size: 14px;
        line-height: 1.6;
      }

      .your-reflection textarea:focus {
        outline: none;
        border-color: #111827;
        box-shadow: 0 0 0 2px rgba(17, 24, 39, 0.12);
      }

      .content-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid rgba(0, 0, 0, 0.1);
        padding: 10px;

        &-text {
          .month {
            font-size: 28px;
            font-weight: 800;
          }

          .week {
            margin-top: 4px;
            color: rgba(0, 0, 0, 0.6);
          }
        }

        &-icon {
          .mood-icon {
            width: 30px;
            height: 30px;
          }
        }
      }

      .content-container {
        padding: 20px;
        flex: auto;
        overflow: auto;

        &-content {
          font-size: 16px;
          line-height: 22px;
          margin-top: 18px;
        }
      }

      .content-rate {
        padding: 8px 20px 0 20px;

        &-tip {
          font-size: 18px;
          font-weight: 800;
        }

        &-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-top: 10px;

          .mood-icon {
            width: 44px;
            height: 44px;
            cursor: pointer;
            transition: transform 0.2s, border 0.2s;

            &.selected {
              border: 2px solid #111827; /* black */
              border-radius: 50%;
              transform: scale(1.08);
            }
          }
        }
      }
    }

    /* right panel */
    &-right {
      width: 50%;
      height: 100%;
      overflow: auto;
      padding: 20px;
      box-sizing: border-box;
      border-left: 1px solid rgba(0, 0, 0, 0.1);
      display: flex;
      flex-direction: column;
      gap: 16px;

      .reflect-btn {
        height: 44px;              /* ← lock height */
        line-height: 44px;         /* ← vertically center text */
        padding: 0 24px;           /* ← horizontal only */
        display: flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
        width: 100%;
        border-radius: 12px;
        border: none;
        background: #111827;
        color: #fff;
        font-weight: 800;
        cursor: pointer;
      }
      .reflect-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .reflect-title {
        font-size: 18px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 10px;
      }

      .reflect-box {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 14px;
        background: #fff;
      }

      .reflect-empty {
        color: rgba(0, 0, 0, 0.55);
        font-style: italic;
      }

      .visual-title {
        font-size: 18px;
        font-weight: 900;
        color: #111827;
        margin-bottom: 10px;
      }

      .content-img {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        flex: none;
        width: 100%;
        padding: 14px;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
      }

      .ai-img {
        width: 100%;
        height: auto;
        border-radius: 14px;
        overflow: hidden;
      }

      .img-text {
        margin-top: 10px;
        color: rgba(0, 0, 0, 0.55);
      }
    }
  }
}
</style>
