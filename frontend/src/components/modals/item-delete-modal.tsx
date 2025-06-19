import {
  Modal,
  Box,
  SpaceBetween,
  Button,
  Alert,
} from "@cloudscape-design/components";
import { Item } from "../../common/types";

export interface ItemDeleteModalProps {
  visible: boolean;
  item?: Item;
  onDelete: () => void;
  onDiscard: () => void;
}

export default function ItemDeleteModal(props: ItemDeleteModalProps) {
  return (
    <Modal
      visible={props.visible}
      onDismiss={props.onDiscard}
      header="Delete Item"
      closeAriaLabel="Close dialog"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={props.onDiscard}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={props.onDelete}
              data-testid="submit"
            >
              Delete
            </Button>
          </SpaceBetween>
        </Box>
      }
    >
      {props.item && (
        <SpaceBetween size="m">
          <Box variant="span">
            Permanently delete item{" "}
            <Box variant="span" fontWeight="bold">
              {props.item.name}
            </Box>
            ? You can't undo this action.
          </Box>
          <Box variant="span">Item Id: {props.item.itemId}</Box>
          <Alert statusIconAriaLabel="Info">
            Proceeding with this action will delete the item.
          </Alert>
        </SpaceBetween>
      )}
    </Modal>
  );
}
