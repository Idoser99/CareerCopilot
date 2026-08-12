const PROFILE_STORAGE_KEY = "career-copilot-profile-id";

class AppState {
  constructor() {
    this.activeTab = "profile";
    this.profiles = [];
    this.profileId = localStorage.getItem(PROFILE_STORAGE_KEY);
  }

  setActiveTab(tab) {
    this.activeTab = tab;
  }

  setProfiles(profiles) {
    this.profiles = Array.isArray(profiles) ? profiles : [];
  }

  selectProfile(profileId) {
    this.profileId = profileId || null;

    if (this.profileId) {
      localStorage.setItem(PROFILE_STORAGE_KEY, this.profileId);
    } else {
      localStorage.removeItem(PROFILE_STORAGE_KEY);
    }
  }

  chooseAvailableProfile() {
    const storedProfileExists = this.profiles.some(
      (profile) => profile.id === this.profileId,
    );

    if (!storedProfileExists) {
      this.selectProfile(this.profiles[0]?.id || null);
    }

    return this.profileId;
  }
}

export const appState = new AppState();
