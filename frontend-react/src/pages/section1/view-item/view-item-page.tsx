import {
  Box,
  BreadcrumbGroup,
  ColumnLayout,
  Container,
  ContentLayout,
  Header,
  SpaceBetween,
  StatusIndicator,
  Tabs,
  Textarea,
} from "@cloudscape-design/components";
import { APP_NAME } from "../../../common/constants";
import { useOnFollow } from "../../../common/hooks/use-on-follow";
import BaseAppLayout from "../../../components/base-app-layout";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import RouterButton from "../../../components/wrappers/router-button";
import { useCallback, useEffect, useState } from "react";
import { Utils } from "../../../common/utils";
import { ApiClient } from "../../../common/api-client/api-client";
import { Item } from "../../../common/types";

export default function ViewItemPage() {
  const onFollow = useOnFollow();
  const navigate = useNavigate();
  const { itemId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [item, setItem] = useState<Item | null>(null);
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") || "main");
  const [value, setValue] = useState("");

  const getItem = useCallback(async () => {
    if (!itemId) return;

    const apiClient = new ApiClient();
    const result = await apiClient.items.getItem(itemId);

    if (!result) {
      navigate("/rag/workspaces");
      return;
    }

    setItem(result);
    setLoading(false);
  }, [navigate, itemId]);

  useEffect(() => {
    getItem();
  }, [getItem]);

  return (
    <BaseAppLayout
      contentType="dashboard"
      breadcrumbs={
        <BreadcrumbGroup
          onFollow={onFollow}
          items={[
            {
              text: APP_NAME,
              href: "/",
            },
            {
              text: "Items",
              href: "/section1",
            },
            {
              text: item?.name || "",
              href: `/section1/items/${itemId}`,
            },
          ]}
        />
      }
      content={
        <ContentLayout
          header={
            <Header
              variant="h1"
              actions={
                <SpaceBetween direction="horizontal" size="xs">
                  <RouterButton data-testid="header-btn-view-details">
                    Delete
                  </RouterButton>
                </SpaceBetween>
              }
            >
              {loading ? (
                <StatusIndicator type="loading">Loading...</StatusIndicator>
              ) : (
                item?.name
              )}
            </Header>
          }
        >
          <SpaceBetween size="l">
            <Container header={<Header variant="h2">Item Settings</Header>}>
              <ColumnLayout columns={3} variant="text-grid">
                <SpaceBetween size="l">
                  <div>
                    <Box variant="awsui-key-label">Item Id</Box>
                    <div>{item?.itemId ?? "loading..."}</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Engine</Box>
                    <div>Test Data</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Name</Box>
                    <div>{item?.name ?? "loading..."}</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Languages</Box>
                    <div>en</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Status</Box>
                    <div>
                      <StatusIndicator type={item?.status ?? "loading"}>
                        In progress
                      </StatusIndicator>
                    </div>
                  </div>
                </SpaceBetween>
                <SpaceBetween size="l">
                  <div>
                    <Box variant="awsui-key-label">Provider</Box>
                    <div>AWS</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Model</Box>
                    <div>Titan</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Dimensions</Box>
                    <div>1024</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Chunk size</Box>
                    <div>512</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Overlap</Box>
                    <div>128</div>
                  </div>
                </SpaceBetween>
                <SpaceBetween size="l">
                  <div>
                    <Box variant="awsui-key-label">Metric</Box>
                    <div>positive</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Indexing</Box>
                    <div>yes</div>
                  </div>
                  <div>
                    <Box variant="awsui-key-label">Hybrid</Box>
                    <div>no</div>
                  </div>
                </SpaceBetween>
              </ColumnLayout>
            </Container>
            <Tabs
              tabs={[
                {
                  label: "Main",
                  id: "main",
                  content: (
                    <Container>
                      <SpaceBetween size="l">
                        <Header
                          variant="h2"
                          actions={<RouterButton>Manage</RouterButton>}
                        >
                          Main
                        </Header>
                        <Textarea
                          onChange={({ detail }) => setValue(detail.value)}
                          value={value}
                          placeholder="This is a placeholder"
                        />
                      </SpaceBetween>
                    </Container>
                  ),
                },
                {
                  label: "Additional",
                  id: "additional",
                  content: <Container>Additional Tab</Container>,
                },
              ]}
              activeTabId={activeTab}
              onChange={({ detail: { activeTabId } }) => {
                setActiveTab(activeTabId);
                setSearchParams((current) => ({
                  ...Utils.urlSearchParamsToRecord(current),
                  tab: activeTabId,
                }));
              }}
            />
          </SpaceBetween>
        </ContentLayout>
      }
    />
  );
}
