import { Injectable } from "@angular/core";
import { AppCheck, getToken } from "@angular/fire/app-check";
import { environment } from "../../environments/environment";

@Injectable({
  providedIn: "root",
})
export class AppCheckService {
  constructor(private appCheck: AppCheck) {}

  async getAppCheckToken(): Promise<string | null> {
    if (!environment.appCheck?.enabled) {
      console.warn("App Check is disabled in this environment");
      return null;
    }

    try {
      const result = await getToken(this.appCheck, false);
      return result.token;
    } catch (error) {
      console.error("Failed to get App Check token:", error);
      return null;
    }
  }
}
