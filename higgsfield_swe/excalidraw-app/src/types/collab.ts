export type Participant = {
  id: string;
  name: string;
  color: string;
  isAI: boolean;
  active: boolean;
};

export type Cursor = {
  userId: string;
  x: number;
  y: number;
  color: string;
};

export type CollabEvent =
  | { event: "join_room"; room_id: string; user_id: string; payload: { name: string; color: string } }
  | { event: "leave_room"; room_id: string; user_id: string }
  | { event: "add_object" | "update_object" | "remove_object"; room_id: string; user_id: string; payload: any }
  | { event: "ai_action"; room_id: string; user_id: string; payload: any }
  | { event: "cursor"; room_id: string; user_id: string; payload: { x: number; y: number } };
