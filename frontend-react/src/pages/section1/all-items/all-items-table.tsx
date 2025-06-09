import {
  TableProps,
  StatusIndicator,
  Table,
  PropertyFilter,
  Pagination,
  Box,
  SpaceBetween,
  Button,
} from "@cloudscape-design/components";
import {
  useCollection,
  PropertyFilterProperty,
  PropertyFilterOperator,
} from "@cloudscape-design/collection-hooks";
import RouterLink from "../../../components/wrappers/router-link";
import { useCallback, useEffect, useState } from "react";
import { TextHelper } from "../../../common/helpers/text-helper";
import { PropertyFilterI18nStrings } from "../../../common/i18n/property-filter-i18n-strings";
import { AllItemsPageHeader } from "./all-items-header";
import { Item } from "../../../common/types";
import { ApiClient } from "../../../common/api-client/api-client";

const ItemsColumnDefinitions: TableProps.ColumnDefinition<Item>[] = [
  {
    id: "name",
    header: "Name",
    sortingField: "name",
    cell: (item) => (
      <RouterLink href={`/section1/items/${item.itemId}`}>
        {item.name}
      </RouterLink>
    ),
    isRowHeader: true,
  },
  {
    id: "type",
    header: "Type",
    sortingField: "type",
    cell: (item) => item.type,
  },
  {
    id: "starus",
    header: "Status",
    sortingField: "status",
    cell: (item) => (
      <StatusIndicator type={item.status}>{item.status}</StatusIndicator>
    ),
    minWidth: 120,
  },
  {
    id: "details",
    header: "Details",
    sortingField: "details",
    cell: (item) => item.details,
  },
];

const ItemColumnFilteringProperties: PropertyFilterProperty[] = [
  {
    propertyLabel: "Name",
    key: "name",
    groupValuesLabel: "Name values",
    operators: [":", "!:", "=", "!="] as PropertyFilterOperator[],
  },
  {
    propertyLabel: "Type",
    key: "type",
    groupValuesLabel: "Type values",
    operators: [":", "!:", "=", "!="] as PropertyFilterOperator[],
  },
  {
    propertyLabel: "Status",
    key: "status",
    groupValuesLabel: "Status values",
    operators: [":", "!:", "=", "!="] as PropertyFilterOperator[],
  },
  {
    propertyLabel: "Details",
    key: "details",
    groupValuesLabel: "Details",
    defaultOperator: ">" as PropertyFilterOperator,
    operators: ["<", "<=", ">", ">="] as PropertyFilterOperator[],
  },
].sort((a, b) => a.propertyLabel.localeCompare(b.propertyLabel));

export default function AllItemsTable() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<Item[]>([]);
  const {
    items,
    actions,
    filteredItemsCount,
    collectionProps,
    paginationProps,
    propertyFilterProps,
  } = useCollection(data, {
    propertyFiltering: {
      filteringProperties: ItemColumnFilteringProperties,
      empty: (
        <Box margin={{ vertical: "xs" }} textAlign="center" color="inherit">
          <div>
            <b>No Items</b>
            <Box variant="p" color="inherit">
              No items associated with this resource.
            </Box>
          </div>
        </Box>
      ),
      noMatch: (
        <Box margin={{ vertical: "xs" }} textAlign="center" color="inherit">
          <SpaceBetween size="xxs">
            <div>
              <b>No matches</b>
              <Box variant="p" color="inherit">
                We can't find a match.
              </Box>
            </div>
            <Button
              onClick={() =>
                actions.setPropertyFiltering({ tokens: [], operation: "and" })
              }
            >
              Clear filter
            </Button>
          </SpaceBetween>
        </Box>
      ),
    },
    pagination: { pageSize: 25 },
    sorting: {
      defaultState: {
        sortingColumn: ItemsColumnDefinitions[0],
        isDescending: true,
      },
    },
    selection: {},
  });

  useEffect(() => {
    (async () => {
      const apiClient = new ApiClient();
      const items = await apiClient.items.getItems();
      setData(items);
      setLoading(false);
    })();
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    const apiClient = new ApiClient();
    const items = await apiClient.items.getItems();
    setData(items);
    setLoading(false);
  }, []);

  return (
    <Table
      {...collectionProps}
      items={items}
      columnDefinitions={ItemsColumnDefinitions}
      selectionType="single"
      variant="full-page"
      stickyHeader={true}
      resizableColumns={true}
      header={
        <AllItemsPageHeader
          selectedItems={collectionProps.selectedItems ?? []}
          refresh={refresh}
          counter={
            loading
              ? undefined
              : TextHelper.getHeaderCounterText(
                  data,
                  collectionProps.selectedItems
                )
          }
        />
      }
      loading={loading}
      loadingText="Loading Items"
      filter={
        <PropertyFilter
          {...propertyFilterProps}
          i18nStrings={PropertyFilterI18nStrings}
          filteringPlaceholder={"Filter Items"}
          countText={TextHelper.getTextFilterCounterText(filteredItemsCount)}
          expandToViewport={true}
        />
      }
      pagination={<Pagination {...paginationProps} />}
    />
  );
}
