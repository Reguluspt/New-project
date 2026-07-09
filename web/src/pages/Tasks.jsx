import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { DndContext, DragOverlay, useDroppable } from '@dnd-kit/core';
import { SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Avatar, Button, Card, Skeleton, Tag, message } from 'antd';
import { EditOutlined, HolderOutlined, PlusOutlined } from '@ant-design/icons';

import client from '../api/client';
import TaskModal from '../components/tasks/TaskModal';

const priorityLabels = {
  low: 'Thấp',
  medium: 'Trung bình',
  high: 'Cao',
};

const priorityColors = {
  low: 'green',
  medium: 'orange',
  high: 'red',
};

const columnDefinitions = [
  { id: 'todo', title: 'Cần làm', color: 'default' },
  { id: 'in_progress', title: 'Đang làm', color: 'processing' },
  { id: 'review', title: 'Đánh giá', color: 'warning' },
  { id: 'done', title: 'Hoàn thành', color: 'success' },
];

function buildColumns(tasks) {
  return columnDefinitions.map((definition) => ({
    ...definition,
    tasks: tasks.filter((task) => (task.status || 'todo') === definition.id),
  }));
}

function formatDueDate(value) {
  if (!value) return 'Chưa có hạn';
  const date = new Date(String(value).replace(' ', 'T'));
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function initials(value) {
  return String(value || 'CV').trim().slice(0, 2).toUpperCase();
}

function TaskCardContent({ task, onEdit }) {
  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 8,
          marginBottom: 10,
        }}
      >
        <div style={{ fontWeight: 650, color: '#111827', lineHeight: 1.35 }}>
          {task.title}
        </div>
        {onEdit ? (
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={(event) => {
              event.stopPropagation();
              onEdit(task);
            }}
            aria-label="Chỉnh sửa công việc"
          />
        ) : null}
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
          marginBottom: 10,
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Tag color={priorityColors[task.priority] || 'default'} style={{ width: 'fit-content' }}>
            {priorityLabels[task.priority] || task.priority || 'Chưa đặt'}
          </Tag>
          <span style={{ fontSize: 12, color: '#64748b' }}>Hạn: {formatDueDate(task.due_date)}</span>
        </div>
        <Avatar size={30} style={{ backgroundColor: '#007f7a', fontWeight: 700 }}>
          {initials(task.assigned_to)}
        </Avatar>
      </div>

      <div
        style={{
          borderTop: '1px solid #e2e8f0',
          paddingTop: 8,
          color: '#475569',
          fontSize: 12,
          lineHeight: 1.5,
        }}
      >
        <div>
          <strong>HĐ: </strong>
          {task.case_id && task.case_contract_number ? (
            <Link to={`/cases/${task.case_id}`}>{task.case_contract_number}</Link>
          ) : (
            <span>Chưa liên kết</span>
          )}
        </div>
        <div>
          <strong>Tên khách hàng: </strong>
          <span>{task.case_customer_info || 'Chưa có'}</span>
        </div>
        <div>
          <strong>Ghi chú: </strong>
          <span>{task.case_note || task.description || 'Chưa có'}</span>
        </div>
      </div>
    </>
  );
}

function SortableTaskCard({ task, onEdit }) {
  const {
    attributes,
    listeners,
    setActivatorNodeRef,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  return (
    <Card
      ref={setNodeRef}
      size="small"
      style={{
        borderRadius: 8,
        border: '1px solid #e2e8f0',
        boxShadow: isDragging
          ? '0 12px 28px rgba(15, 23, 42, 0.16)'
          : '0 4px 14px rgba(15, 23, 42, 0.06)',
        opacity: isDragging ? 0.7 : 1,
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      styles={{ body: { padding: 12 } }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
        <Button
          ref={setActivatorNodeRef}
          type="text"
          size="small"
          icon={<HolderOutlined />}
          style={{ cursor: 'grab', color: '#94a3b8', flexShrink: 0 }}
          {...attributes}
          {...listeners}
          aria-label="Kéo thả công việc"
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <TaskCardContent task={task} onEdit={onEdit} />
        </div>
      </div>
    </Card>
  );
}

function KanbanColumn({ column, onEditTask }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  return (
    <section
      ref={setNodeRef}
      style={{
        minWidth: 300,
        background: isOver ? '#eef6ff' : '#f8fafc',
        border: `1px solid ${isOver ? '#007f7a' : '#d8e7e5'}`,
        borderRadius: 8,
        padding: 12,
        transition: 'background 0.16s ease, border-color 0.16s ease',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#0f172a', margin: 0 }}>
          {column.title}
        </h2>
        <Tag color={column.color}>{column.tasks.length}</Tag>
      </div>

      <SortableContext
        items={column.tasks.map((task) => task.id)}
        strategy={verticalListSortingStrategy}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minHeight: 80 }}>
          {column.tasks.map((task) => (
            <SortableTaskCard key={task.id} task={task} onEdit={onEditTask} />
          ))}
        </div>
      </SortableContext>
    </section>
  );
}

function replaceTask(columns, taskId, nextTask) {
  return columns.map((column) => ({
    ...column,
    tasks: column.tasks.map((task) => (task.id === taskId ? { ...task, ...nextTask } : task)),
  }));
}

export default function Tasks() {
  const [columns, setColumns] = useState(buildColumns([]));
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [taskModalOpen, setTaskModalOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);

  const loadTasks = useCallback(async () => {
    setLoadingTasks(true);
    try {
      const response = await client.get('/tasks');
      setColumns(buildColumns(response.data?.items || []));
    } catch (error) {
      console.error('Không thể tải danh sách công việc', error);
      message.error('Không thể tải danh sách công việc');
    } finally {
      setLoadingTasks(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const taskLocationById = useMemo(() => {
    const locations = new Map();
    columns.forEach((column) => {
      column.tasks.forEach((task) => {
        locations.set(task.id, { columnId: column.id, task });
      });
    });
    return locations;
  }, [columns]);

  const activeTask = activeTaskId ? taskLocationById.get(activeTaskId)?.task : null;

  const findColumnIdForOver = useCallback((overId) => {
    if (!overId) return null;
    if (columns.some((column) => column.id === overId)) return overId;
    return taskLocationById.get(overId)?.columnId || null;
  }, [columns, taskLocationById]);

  const openCreateModal = useCallback(() => {
    setEditingTask(null);
    setTaskModalOpen(true);
  }, []);

  const openEditModal = useCallback((task) => {
    setEditingTask(task);
    setTaskModalOpen(true);
  }, []);

  const closeTaskModal = useCallback(() => {
    setTaskModalOpen(false);
    setEditingTask(null);
  }, []);

  const handleModalSubmit = useCallback(async (payload) => {
    if (editingTask) {
      const response = await client.put(`/tasks/${editingTask.id}`, payload);
      setColumns((currentColumns) => replaceTask(currentColumns, editingTask.id, response.data));
      message.success('Đã cập nhật công việc');
    } else {
      const response = await client.post('/tasks', { ...payload, status: 'todo' });
      setColumns((currentColumns) => currentColumns.map((column) => (
        column.id === 'todo'
          ? { ...column, tasks: [...column.tasks, response.data] }
          : column
      )));
      message.success('Đã tạo công việc');
    }
    closeTaskModal();
  }, [closeTaskModal, editingTask]);

  const handleDragStart = useCallback((event) => {
    setActiveTaskId(event.active.id);
  }, []);

  const handleDragEnd = useCallback((event) => {
    const { active, over } = event;
    setActiveTaskId(null);

    if (!over) return;

    const activeId = active.id;
    const source = taskLocationById.get(activeId);
    const targetColumnId = findColumnIdForOver(over.id);

    if (!source || !targetColumnId || source.columnId === targetColumnId) return;

    setColumns((currentColumns) => currentColumns.map((column) => {
      if (column.id === source.columnId) {
        return {
          ...column,
          tasks: column.tasks.filter((task) => task.id !== activeId),
        };
      }
      if (column.id === targetColumnId) {
        return {
          ...column,
          tasks: [...column.tasks, { ...source.task, status: targetColumnId }],
        };
      }
      return column;
    }));

    client.put(`/tasks/${activeId}`, { status: targetColumnId }).catch((error) => {
      console.error('Không thể cập nhật trạng thái công việc', error);
      message.error('Không thể cập nhật trạng thái công việc');
      loadTasks();
    });
  }, [findColumnIdForOver, loadTasks, taskLocationById]);

  const handleDragCancel = useCallback(() => {
    setActiveTaskId(null);
  }, []);

  return (
    <div style={{ padding: '0 0 24px 0' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 16,
          marginBottom: 20,
        }}
      >
        <div>
          <h1 style={{ fontSize: 32, fontWeight: 760, color: '#0f172a', margin: 0 }}>
            Quản lý công việc
          </h1>
          <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
            Theo dõi tiến độ công việc theo bảng Kanban.
          </div>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreateModal}>
          Tạo công việc
        </Button>
      </div>

      {loadingTasks ? (
        <Card style={{ borderRadius: 8, border: '1px solid #d8e7e5' }}>
          <Skeleton active paragraph={{ rows: 5 }} />
        </Card>
      ) : (
        <DndContext
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(4, minmax(300px, 1fr))',
              gap: 16,
              overflowX: 'auto',
              paddingBottom: 8,
            }}
          >
            {columns.map((column) => (
              <KanbanColumn key={column.id} column={column} onEditTask={openEditModal} />
            ))}
          </div>

          <DragOverlay>
            {activeTask ? (
              <Card
                size="small"
                style={{
                  width: 300,
                  borderRadius: 8,
                  border: '1px solid #dbeafe',
                  boxShadow: '0 18px 36px rgba(15, 23, 42, 0.22)',
                  cursor: 'grabbing',
                }}
                styles={{ body: { padding: 12 } }}
              >
                <TaskCardContent task={activeTask} />
              </Card>
            ) : null}
          </DragOverlay>
        </DndContext>
      )}

      <TaskModal
        open={taskModalOpen}
        task={editingTask}
        onCancel={closeTaskModal}
        onSubmit={handleModalSubmit}
      />
    </div>
  );
}
