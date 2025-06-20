import { get, put, del } from "aws-amplify/api";
import { Item } from "../types";
import { API_NAME } from "../constants";
import { ApiClientBase } from "./api-client-base";

export class ItemsApiClient extends ApiClientBase {
  async getItems(): Promise<Item[]> {
    const headers = await this.getHeaders();
    const restOperation = get({
      apiName: API_NAME,
      path: "/items",
      options: {
        headers,
      },
    });

    const response = await restOperation.response;
    const { data = [] } = (await response.body.json()) as any;

    return data;
  }

  async addItem(item: Omit<Item, "itemId">): Promise<boolean> {
    const headers = await this.getHeaders();
    const restOperation = put({
      apiName: API_NAME,
      path: "/items",
      options: {
        headers,
        body: {
          ...item,
        },
      },
    });

    const response = await restOperation.response;
    const data = (await response.body.json()) as any;

    return data.ok;
  }

  async getItem(id: string): Promise<Item> {
    const headers = await this.getHeaders();
    const restOperation = get({
      apiName: API_NAME,
      path: `/items/${id}`,
      options: {
        headers,
      },
    });

    const response = await restOperation.response;
    const { data } = (await response.body.json()) as any;

    return data;
  }

  async deleteItem(id: string): Promise<void> {
    const headers = await this.getHeaders();
    const restOperation = del({
      apiName: API_NAME,
      path: `/items/${id}`,
      options: {
        headers,
      },
    });

    await restOperation.response;
  }
}
