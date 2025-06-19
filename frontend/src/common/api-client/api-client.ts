import { ItemsApiClient } from "./items-api-client";

export class ApiClient {
  private _itemsClient: ItemsApiClient | undefined;

  public get items() {
    if (!this._itemsClient) {
      this._itemsClient = new ItemsApiClient();
    }

    return this._itemsClient;
  }
}
