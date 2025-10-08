// playlist_backend.c
// Compile to shared library: libplaylist.so (Linux/mac) or playlist_backend.dll (Windows)

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_SONGS 2000
#define MAX_NAME 256

// ---------------- Trie Node for Search -----------------
typedef struct TrieNode {
    struct TrieNode* children[26];
    int isEndOfWord;
    char songName[MAX_NAME];
} TrieNode;

TrieNode* createNode() {
    TrieNode* node = (TrieNode*)malloc(sizeof(TrieNode));
    if (!node) return NULL;
    node->isEndOfWord = 0;
    node->songName[0] = '\0';
    for (int i = 0; i < 26; i++) node->children[i] = NULL;
    return node;
}

void freeTrie(TrieNode* root) {
    if (!root) return;
    for (int i = 0; i < 26; i++)
        if (root->children[i]) freeTrie(root->children[i]);
    free(root);
}

static TrieNode* globalRoot = NULL;

static void sanitize_and_lower(const char* input, char* out) {
    int j = 0;
    for (int i = 0; input[i] != '\0' && j < MAX_NAME-1; i++) {
        char c = input[i];
        if (c >= 'A' && c <= 'Z') c = c - 'A' + 'a';
        if ((c >= 'a' && c <= 'z') || c == ' ') {
            out[j++] = c;
        }
    }
    out[j] = '\0';
}

void insertSong(TrieNode* root, const char* word) {
    if (!root || !word) return;
    char cleaned[MAX_NAME]; sanitize_and_lower(word, cleaned);
    TrieNode* curr = root;
    for (int i = 0; cleaned[i] != '\0'; i++) {
        char ch = cleaned[i];
        if (ch == ' ') continue;
        int index = ch - 'a';
        if (index < 0 || index >= 26) continue;
        if (!curr->children[index]) curr->children[index] = createNode();
        curr = curr->children[index];
    }
    curr->isEndOfWord = 1;
    strncpy(curr->songName, cleaned, MAX_NAME-1);
}

int searchSong(TrieNode* root, const char* word) {
    if (!root || !word) return 0;
    char cleaned[MAX_NAME]; sanitize_and_lower(word, cleaned);
    TrieNode* curr = root;
    for (int i = 0; cleaned[i] != '\0'; i++) {
        char ch = cleaned[i];
        if (ch == ' ') continue;
        int index = ch - 'a';
        if (index < 0 || index >= 26) return 0;
        if (!curr->children[index]) return 0;
        curr = curr->children[index];
    }
    return curr->isEndOfWord;
}

// ---------------- Heap for Most Played -----------------
typedef struct {
    char name[MAX_NAME];
    int plays;
} Song;

static Song heap[MAX_SONGS];
static int heapSize = 0;

void swapSong(Song* a, Song* b) {
    Song temp = *a; *a = *b; *b = temp;
}

void heapifyUp(int index) {
    while (index > 0 && heap[(index-1)/2].plays < heap[index].plays) {
        swapSong(&heap[index], &heap[(index-1)/2]);
        index = (index-1)/2;
    }
}

void heapifyDown(int index) {
    int largest = index;
    int left = 2*index + 1;
    int right = 2*index + 2;
    if (left < heapSize && heap[left].plays > heap[largest].plays) largest = left;
    if (right < heapSize && heap[right].plays > heap[largest].plays) largest = right;
    if (largest != index) {
        swapSong(&heap[index], &heap[largest]);
        heapifyDown(largest);
    }
}

void addSongPlayInternal(const char* name) {
    if (!name) return;
    char cleaned[MAX_NAME]; sanitize_and_lower(name, cleaned);
    for (int i = 0; i < heapSize; i++) {
        if (strcmp(heap[i].name, cleaned) == 0) {
            heap[i].plays++;
            heapifyUp(i);
            return;
        }
    }
    if (heapSize >= MAX_SONGS) return;
    strncpy(heap[heapSize].name, cleaned, MAX_NAME-1);
    heap[heapSize].plays = 1;
    heapifyUp(heapSize);
    heapSize++;
}

const char* getMostPlayed() {
    if (heapSize == 0) return "";
    return heap[0].name;
}

// ---------------- Save/Load song names to a text file -----------------
void save_songs_to_file(const char* filename) {
    if (!filename || !globalRoot) return;
    FILE* fp = fopen(filename, "w");
    if (!fp) return;
    // DFS to collect words
    char buffer[MAX_NAME];
    // recursive lambda-like via function pointer
    void dfs(TrieNode* node) {
        if (!node) return;
        if (node->isEndOfWord) {
            fprintf(fp, "%s\n", node->songName);
        }
        for (int i = 0; i < 26; i++) {
            if (node->children[i]) {
                dfs(node->children[i]);
            }
        }
    }
    dfs(globalRoot);
    fclose(fp);
}

void load_songs_from_file(const char* filename) {
    if (!filename || !globalRoot) return;
    FILE* fp = fopen(filename, "r");
    if (!fp) return;
    char line[MAX_NAME];
    while (fgets(line, sizeof(line), fp)) {
        size_t L = strlen(line);
        if (L > 0 && (line[L-1] == '\n' || line[L-1] == '\r')) line[L-1] = '\0';
        if (strlen(line) > 0) insertSong(globalRoot, line);
    }
    fclose(fp);
}

// ---------------- Exported API -----------------
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

#include <stdint.h>

EXPORT void initSystem() {
    if (globalRoot) {
        freeTrie(globalRoot);
        globalRoot = NULL;
    }
    globalRoot = createNode();
    heapSize = 0;
}

EXPORT void add_song(const char* song) {
    if (!globalRoot) initSystem();
    insertSong(globalRoot, song);
}

EXPORT int search_song(const char* song) {
    if (!globalRoot) return 0;
    return searchSong(globalRoot, song);
}

EXPORT void play_song(const char* song) {
    addSongPlayInternal(song);
}

EXPORT const char* most_played() {
    const char* s = getMostPlayed();
    if (!s) return "";
    return s;
}

EXPORT void save_songs(const char* filename) {
    save_songs_to_file(filename);
}

EXPORT void load_songs(const char* filename) {
    if (!globalRoot) initSystem();
    load_songs_from_file(filename);
}
