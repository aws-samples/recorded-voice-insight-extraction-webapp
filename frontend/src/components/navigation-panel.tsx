import {
  SideNavigation,
  SideNavigationProps,
} from "@cloudscape-design/components";
import { useNavigationPanelState } from "../common/hooks/use-navigation-panel-state";
import { useState } from "react";
import { useOnFollow } from "../common/hooks/use-on-follow";
import { useLocation } from "react-router-dom";

export default function NavigationPanel() {
  const location = useLocation();
  const onFollow = useOnFollow();
  const [navigationPanelState, setNavigationPanelState] =
    useNavigationPanelState();

  const [items] = useState<SideNavigationProps.Item[]>(() => {
    const items: SideNavigationProps.Item[] = [
      {
        type: "link",
        text: "Home",
        href: "/home",
      },
      {
        type: "link",
        text: "File Management",
        href: "/file-management",
      },
      {
        type: "link",
        text: "Chat With Your Media",
        href: "/chat-with-media",
      },
      {
        type: "link",
        text: "Analyze Your Media",
        href: "/analyze",
      },
    ];

    items.push(
      { type: "divider" },
      {
        type: "link",
        text: "Documentation",
        href: "https://github.com/aws-samples/recorded-voice-insight-extraction-webapp",
        external: true,
      }
    );

    return items;
  });

  const onChange = ({
    detail,
  }: {
    detail: SideNavigationProps.ChangeDetail;
  }) => {
    const sectionIndex = items.indexOf(detail.item);
    setNavigationPanelState({
      collapsedSections: {
        ...navigationPanelState.collapsedSections,
        [sectionIndex]: !detail.expanded,
      },
    });
  };

  return (
    <SideNavigation
      onFollow={onFollow}
      onChange={onChange}
      header={{ href: "/home", text: "Pages" }}
      activeHref={location.pathname}
      items={items.map((value, idx) => {
        const item = { ...value };
        
        if (item.type === "section") {
          const collapsed =
            navigationPanelState.collapsedSections?.[idx] === true;
          item.defaultExpanded = !collapsed;
        }

        return item;
      })}
    />
  );
}
